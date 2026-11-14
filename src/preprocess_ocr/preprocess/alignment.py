"""
Alignment between the cleaned text and the RAW text.

Every cleaning step is a list of Edit(start, end, new) on the CURRENT text. AlignedText applies them and keeps, for every character of the
cleaned text, the index of the raw character it came from (`raw_index`, non-decreasing). That is what keeps all offsets usable:

    raw_span(start, end)         a span of the cleaned text -> the span of the raw text (NER output back to the offsets of the gold data)
    clean_span(raw_start, end)   a span of the raw text -> the span of the cleaned text (move existing annotations; None if it was deleted)

Rules of the mapping: a 1:1 replacement keeps the raw index of each character; a joined word ("AMSTER\nDAM" -> "AMSTERDAM") keeps the raw index of every
letter, so its raw span still covers the line break; an inserted character takes the raw index of the character before it; a deletion just disappears.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Edit:
    start: int                           # replaces text[start:end] ...
    end: int
    new: str = ""                        # ... by this
    src: tuple[int, ...] | None = None   # optional: for every new character the index in the CURRENT text it comes from


class AlignedText:
    def __init__(self, text: str, raw_index: list[int]):
        assert len(text) == len(raw_index)
        self.text, self.raw_index = text, raw_index

    @classmethod
    def of(cls, raw: str) -> "AlignedText":
        return cls(raw, list(range(len(raw))))

    def apply(self, edits: Iterable[Edit]) -> "AlignedText":
        """A new AlignedText with the edits applied (they must not overlap)."""
        parts: list[str] = []
        idx: list[int] = []
        pos = 0
        for e in sorted(edits, key=lambda e: (e.start, e.end)):
            if e.start < pos:
                raise ValueError(f"overlapping edits at {e.start}")
            parts.append(self.text[pos:e.start])
            idx.extend(self.raw_index[pos:e.start])
            if e.src is not None:
                new, new_idx = e.new, [self.raw_index[i] for i in e.src]
            elif len(e.new) == e.end - e.start:
                new, new_idx = e.new, self.raw_index[e.start:e.end]
            elif e.new:
                base = (self.raw_index[e.start] if e.end > e.start else
                        self.raw_index[e.start - 1] if e.start > 0 else self.raw_index[0] if self.raw_index else 0)
                new, new_idx = e.new, [base] * len(e.new)
            else:
                new, new_idx = "", []
            parts.append(new)
            idx.extend(new_idx)
            pos = e.end
        parts.append(self.text[pos:])
        idx.extend(self.raw_index[pos:])
        return AlignedText("".join(parts), idx)

    def raw_span(self, start: int, end: int) -> tuple[int, int]:
        """Span of the cleaned text -> span of the raw text."""
        if end <= start:
            i = self.raw_index[min(start, len(self.raw_index) - 1)] if self.raw_index else 0
            return i, i
        return self.raw_index[start], self.raw_index[end - 1] + 1

    def clean_span(self, raw_start: int, raw_end: int) -> tuple[int, int] | None:
        """Span of the raw text -> span of the cleaned text; None if every character of it was deleted."""
        i = bisect_left(self.raw_index, raw_start)
        j = bisect_right(self.raw_index, raw_end - 1) - 1
        return (i, j + 1) if i <= j else None

    def clean_position(self, raw_pos: int) -> int:
        """First cleaned index that comes from raw position >= raw_pos."""
        return bisect_left(self.raw_index, raw_pos)

    # ---- compact storage of the mapping: runs [cleaned start, raw start, length] where the raw index grows by 1
    def to_runs(self) -> list[list[int]]:
        runs: list[list[int]] = []
        for i, r in enumerate(self.raw_index):
            if runs and r == runs[-1][1] + runs[-1][2]:
                runs[-1][2] += 1
            else:
                runs.append([i, r, 1])
        return runs

    @classmethod
    def from_runs(cls, text: str, runs: list[list[int]]) -> "AlignedText":
        idx: list[int] = []
        for _, raw, n in runs:
            idx.extend(range(raw, raw + n))
        return cls(text, idx)
