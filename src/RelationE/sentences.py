"""Sentence segmentation without a heavy dependency, and the assignment of mentions to sentences. A spaCy pipeline can be used instead (spacy_sentence_spans)."""
from __future__ import annotations

import re
from bisect import bisect_right
from typing import Iterable

from .models import Mention

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

def get_character_distance(
    entity1: Mention,
    entity2: Mention,
) -> int:
    """
    Return the number of characters between two mention spans.

    Returns zero if spans overlap.
    """

    left, right = sorted(
        [entity1, entity2],
        key=lambda entity: entity.start,
    )

    return max(0, right.start - left.end)


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

def get_context_boundaries(
    entity1: Mention,
    entity2: Mention,
    text: str,
    sentence_spans: list[tuple[int, int]],
    padding: int,
) -> tuple[int, int]:
    """
    Extract a context window covering the sentences containing
    both mentions.

    If sentence assignments are unavailable, use the mention
    spans directly.
    """

    if (
        entity1.sentence_id is not None
        and entity2.sentence_id is not None
    ):

        first = min(
            entity1.sentence_id,
            entity2.sentence_id,
        )

        last = max(
            entity1.sentence_id,
            entity2.sentence_id,
        )

        start = sentence_spans[first][0]
        end = sentence_spans[last][1]

    else:

        start = min(entity1.start, entity2.start)
        end = max(entity1.end, entity2.end)

    start = max(0, start - padding)
    end = min(len(text), end + padding)

    return start, end
