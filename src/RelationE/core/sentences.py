"""Sentence segmentation without a heavy dependency, and the assignment of mentions to sentences. A spaCy pipeline can be used instead (spacy_sentence_spans)."""
from __future__ import annotations

import re
from bisect import bisect_right
from typing import Iterable

from ..dataLayer.models import Mention
from src.configs.re_cfg import CandidateConfig

_BOUNDARY = re.compile(r"(?<=[.!?])[\"')\]]*\s+(?=[A-Z0-9\"'(])")
_ABBREVIATIONS = frozenset("dr mr prof ir jhr st gen kol maj kapt luit adm mevr mej nr no blz enz bijv ca vgl".split())


def sentence_spans(text: str) -> list[tuple[int, int]]:
    """
    (start, end) of every sentence: a period/question/exclamation mark followed by
    space and a capital or digit, but not after an abbreviation or an initial.
    """
    cuts = {0, len(text)}
    for m in _BOUNDARY.finditer(text):
        before = re.search(r"(\w+)\.$", text[max(0, m.start() - 16):m.start()])
        if before and (before.group(1).lower() in _ABBREVIATIONS or (len(before.group(1)) == 1 and before.group(1).isupper())):
            continue
        cuts.add(m.end())
    points = sorted(cuts)
    spans = []
    for a, b in zip(points, points[1:]):
        seg = text[a:b]
        lead, trail = len(seg) - len(seg.lstrip()), len(seg) - len(seg.rstrip())
        if b - trail > a + lead:
            spans.append((a + lead, b - trail))
    return spans or [(0, len(text))]


def spacy_sentence_spans(nlp, text: str) -> list[tuple[int, int]]:
    """Sentence spans from a spaCy pipeline with a parser or a sentencizer."""
    try:
        return [(s.start_char, s.end_char) for s in nlp(text).sents]
    except ValueError as exc:
        raise ValueError("spaCy sentence boundaries are unavailable: load a pipeline with a parser or add a sentencizer") from exc


def assign_sentence_ids(mentions: Iterable[Mention], spans: list[tuple[int, int]]) -> None:
    """Set mention.sentence_id: the sentence that contains the midpoint of the mention, otherwise the one with the largest overlap (None if the mention overlaps none)."""
    starts = [s for s, _ in spans]
    for m in mentions:
        mid = (m.start + m.end) // 2
        i = bisect_right(starts, mid) - 1
        if 0 <= i < len(spans) and spans[i][0] <= mid < spans[i][1]:
            m.sentence_id = i
            continue
        overlaps = [(max(0, min(m.end, e) - max(m.start, s)), -k) for k, (s, e) in enumerate(spans)]
        best = max(overlaps, default=(0, 0))
        m.sentence_id = -best[1] if best[0] > 0 else None


# ---------------------------------------------------------
# Distance calculation
# ---------------------------------------------------------

def character_distance(m1: Mention, m2: Mention) -> int:
    left, right = sorted((m1, m2), key=lambda m: (m.start, m.end))
    return max(0, right.start - left.end)


def sentence_distance(m1: Mention, m2: Mention) -> int | None:
    return None if m1.sentence_id is None or m2.sentence_id is None else abs(m1.sentence_id - m2.sentence_id)



def is_within_sentence_distance(
    entity1: Mention,
    entity2: Mention,
    max_sentence_distance: int,
) -> bool:
    """
    Check sentence proximity.

    If either sentence assignment is unknown, return True and
    let character distance act as the fallback filter.
    """

    if (
        entity1.sentence_id is None
        or entity2.sentence_id is None
    ):
        return True

    distance = abs(
        entity1.sentence_id - entity2.sentence_id
    )

    return distance <= max_sentence_distance


# ---------------------------------------------------------
# Context extraction
# ---------------------------------------------------------

def _snap_left(text: str, pos: int) -> int:
    while pos > 0 and not text[pos - 1].isspace():
        pos -= 1
    return pos


def _snap_right(text: str, pos: int) -> int:
    while pos < len(text) and not text[pos].isspace():
        pos += 1
    return pos


def context_boundaries(m1: Mention, m2: Mention, text: str, spans: list[tuple[int, int]], cfg: CandidateConfig) -> tuple[int, int]:
    """The sentences of both mentions (or the mentions themselves without sentence ids) plus padding; always contains both mentions completely; capped at max_context_chars."""
    lo, hi = min(m1.start, m2.start), max(m1.end, m2.end)
    if m1.sentence_id is not None and m2.sentence_id is not None:
        a, b = sorted((m1.sentence_id, m2.sentence_id))
        start, end = min(spans[a][0], lo), max(spans[b][1], hi)
    else:
        start, end = lo, hi
    if end - start > cfg.max_context_chars:
        start, end = lo, hi
    start, end = max(0, start - cfg.context_padding), min(len(text), end + cfg.context_padding)
    return _snap_left(text, start), _snap_right(text, end)