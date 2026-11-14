"""
Sentence segmentation for the cleaned bulletins.

The cleaned text is ONE line (every run of whitespace, line breaks included, has been
collapsed to a single space). To get sentences we:

  1. Split on [.!?] followed by whitespace + a capital letter or a digit
     (so "11 uur." at end-of-bulletin ends a sentence even if the next char is a digit).
  2. Do NOT split after known abbreviations: ``mr.``, ``dr.``, ``N.V.``, ``z.g.``,
     ``U.S.``, ``No.``, ``vs.``, ``etc.`` ... plus the cardinal-direction ``Z.W.``,
     ``N.O.`` etc. and time-ish ``a.s.``, ``p.m.`` (English leaks in).
  3. Do NOT split inside a number with a decimal point or between a digit and a unit
     ("64 7/8" stays together; "1939." at the start of a bulletin header is handled by
     the block_starts below, not by this rule).
  4. Force a hard sentence break at every offset in ``CleanResult.block_starts``
     (these are the bulletin header, section headers, removed number lines and blank
     lines: they separate items even when punctuation is missing).

The output is a list of ``Sentence(start, end, text)`` where ``start`` and ``end`` are
offsets in the CLEANED text (so they round-trip to raw via ``CleanResult.raw_span``).

This is intentionally simple: a real sentence splitter (PySBD / stanza / wtpsplit) is
overkill for an OCR'd 1939 corpus and would itself be confused by the noise that the
cleaner did not catch. If you ever need better recall on abbreviations, extend
``ABBREVIATIONS`` rather than swapping the engine.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from .pipeline import CleanResult


#: abbreviations whose trailing period does NOT end a sentence.
#: lower-cased, no trailing dot. Single-letter abbreviations (``w.``, ``n.``) are too
#: noisy to whitelist here; they are caught by the "next char is lowercase" guard instead.
ABBREVIATIONS: frozenset[str] = frozenset({
    # titles
    "mr", "mrs", "dr", "prof", "ir", "ds", "bnd", "jr", "sr",
    # corporate / commercial
    "n.v", "v.o.f", "s.a", "b.v", "c.v", "mij", "coop",
    # generic
    "etc", "ca", "vs", "no", "nl", "zn", "p.t.t", "n.s", "as",
    # Dutch honorifics / regal
    "z.h", "h.m", "z.m", "k.h", "p.w", "h.h",
    # directions and time
    "n.o", "z.o", "n.w", "z.w", "n.z", "a.s", "p.m", "a.m", "v.m",
    # OCR-leak English
    "mr", "mrs", "st",
    # dates / numerals
    "blz", "pag", "art",
})


_END = ".!?"
_WS = r"[ \t]"
_CAP_OR_DIGIT = r"[A-ZÀ-Ý0-9IlO]"   # I/l/O are OCR for 1; treat as a number-start too

#: a candidate end-of-sentence: ``.!?`` + whitespace + capital/digit
_CANDIDATE = re.compile(rf"([{re.escape(_END)}])({_WS}+)({_CAP_OR_DIGIT})")

#: the word ending just before the candidate punctuation (without the dot)
_PREV_WORD = re.compile(r"([A-Za-z.]+)\.?$")


@dataclass(frozen=True)
class Sentence:
    start: int          # offset in the CLEANED text (inclusive)
    end: int            # offset in the CLEANED text (exclusive)
    text: str

    def raw_span(self, res: CleanResult) -> tuple[int, int]:
        return res.raw_span(self.start, self.end)

    def to_dict(self, res: CleanResult | None = None) -> dict:
        d = dict(start=self.start, end=self.end, text=self.text)
        if res is not None:
            d["raw_start"], d["raw_end"] = self.raw_span(res)
        return d


def _abbrev_before(text: str, punct_pos: int) -> bool:
    """True if the token just before the punctuation at ``punct_pos`` is an abbreviation."""
    # walk back to the previous whitespace
    j = punct_pos - 1
    while j >= 0 and text[j].isalpha() or (j >= 0 and text[j] == "."):
        j -= 1
    word = text[j + 1:punct_pos].rstrip(".").lower()
    return word in ABBREVIATIONS


def split_sentences(
    res_or_text: CleanResult | str,
    block_starts: Iterable[int] | None = None,
) -> list[Sentence]:
    """
    Split the cleaned text into sentences.

    Parameters
    ----------
    res_or_text
        Either a ``CleanResult`` (preferred: pulls hard sentence breaks automatically)
        or a plain ``str`` (then you must pass ``block_starts`` yourself if you want
        hard breaks at item boundaries).
    block_starts
        Offsets in the cleaned text where a new item/section starts. Always forces a
        sentence break. If ``res_or_text`` is a ``CleanResult`` and this is ``None``,
        ``res_or_text.sentence_breaks`` is used (NOT ``block_starts`` -- removed
        number lines are layout boundaries but not sentence breaks; see
        ``CleanResult.sentence_breaks``). Pass ``res_or_text.block_starts``
        explicitly if you really want the old behaviour.
    """
    if isinstance(res_or_text, CleanResult):
        text = res_or_text.text
        if block_starts is None:
            block_starts = res_or_text.sentence_breaks
    else:
        text = res_or_text

    breaks: set[int] = set()        # cleaned offsets where a sentence ENDS (exclusive)
    for m in _CANDIDATE.finditer(text):
        if _abbrev_before(text, m.start()):
            continue
        # also skip "1939." inside a number-only context, e.g. "10 7/8." at end of a price
        breaks.add(m.end(1))

    # block_starts: each marks the BEGINNING of a new item -> the previous sentence ends here
    for b in sorted(block_starts):
        if 0 < b <= len(text):
            breaks.add(b)

    # also always end at end of text
    breaks.add(len(text))

    out: list[Sentence] = []
    start = 0
    for end in sorted(b for b in breaks if b > 0):
        # trim whitespace-only leading bits
        s = start
        while s < end and text[s] == " ":
            s += 1
        if s < end:
            out.append(Sentence(s, end, text[s:end].strip()))
        start = end
    # merge the last dangling chunk if any
    if start < len(text):
        s = start
        while s < len(text) and text[s] == " ":
            s += 1
        if s < len(text):
            out.append(Sentence(s, len(text), text[s:].strip()))
    return out


def sentence_for(res: CleanResult, clean_pos: int) -> Sentence | None:
    """Return the sentence that contains the cleaned offset ``clean_pos`` (or None)."""
    for s in split_sentences(res):
        if s.start <= clean_pos < s.end:
            return s
    return None
