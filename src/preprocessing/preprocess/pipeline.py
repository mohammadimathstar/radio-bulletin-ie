"""clean(): the whole preprocessing of one text, returning the cleaned text together with everything needed to get back to the raw offsets."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .alignment import AlignedText
from .config import CleanConfig, Span
from .lexicon import Lexicon
from .steps import (MONTH_NUMBER, MONTHS, RunState, fix_digits_letters, fix_punctuation, flatten, join_split_words, normalize_unicode,
                    remove_artifacts, tag_metadata)


@dataclass
class CleanResult:
    text: str                      # the cleaned text: one line, single spaces
    aligned: AlignedText           # cleaned text + the raw index of every character
    raw_length: int
    spans: list[Span]              # metadata and removed artifacts, in RAW offsets
    block_starts: list[int]        # offsets in the CLEANED text where a new item/section starts (layout info)
    sentence_breaks: list[int]     # subset of block_starts that are HARD sentence breaks (section headers,
                                   #   bulletin headers, blank lines). Removed number lines are NOT here.
                                   #   Pass this to split_sentences() for clean sentence context.
    stats: dict[str, int]          # how often every rule fired
    date_in_text: str | None       # the date in the header of the bulletin (ISO), after the digit repairs

    def raw_span(self, start: int, end: int) -> tuple[int, int]:
        """Span of the cleaned text -> span of the raw text (NER output back to the offsets of the raw data)."""
        return self.aligned.raw_span(start, end)

    def clean_span(self, raw_start: int, raw_end: int) -> tuple[int, int] | None:
        """Span of the raw text -> span of the cleaned text (existing annotations); None if all of it was removed."""
        return self.aligned.clean_span(raw_start, raw_end)

    def to_dict(self, include_map: bool = True) -> dict[str, Any]:
        d = dict(text=self.text, raw_length=self.raw_length, spans=[s.to_dict() for s in self.spans],
                 block_starts=self.block_starts, sentence_breaks=self.sentence_breaks,
                 stats=self.stats, date_in_text=self.date_in_text)
        if include_map:
            d["offset_runs"] = self.aligned.to_runs()          # [cleaned start, raw start, length] runs; see AlignedText.from_runs
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CleanResult":
        aligned = AlignedText.from_runs(d["text"], d["offset_runs"])
        return cls(d["text"], aligned, d["raw_length"], [Span(**s) for s in d["spans"]],
                   d["block_starts"], d.get("sentence_breaks", d["block_starts"]),
                   d["stats"], d.get("date_in_text"))


def clean(raw: str, cfg: CleanConfig | None = None, lexicon: Lexicon | None = None) -> CleanResult:
    """Clean one text (see steps.py for the steps). Without a lexicon the repairs that need one (split words, checked digit/letter fixes) are skipped."""
    cfg = cfg or CleanConfig()
    
    run = RunState(cfg, lexicon)
    at = AlignedText.of(raw)
    if cfg.unicode:
        at = normalize_unicode(at, run)
    at = tag_metadata(at, run)
    if cfg.artifacts:
        at = remove_artifacts(at, run)
    if cfg.join_words:
        at = join_split_words(at, run)
    if cfg.digits_letters:
        at = fix_digits_letters(at, run)
    if cfg.punctuation:
        at = fix_punctuation(at, run)
    at = flatten(at, run)
    starts = sorted({min(at.clean_position(b), len(at.text)) for b in run.boundaries} - {len(at.text)})
    hard = sorted({min(at.clean_position(b), len(at.text)) for b in run.sentence_breaks} - {len(at.text)})
    m = re.search(rf"\b(\d{{1,2}}) ((?i:{MONTHS})) (\d{{4}})\b", at.text[:300])
    date = f"{m.group(3)}-{MONTH_NUMBER[m.group(2).lower()]:02d}-{int(m.group(1)):02d}" if m else None
    return CleanResult(at.text, at, len(raw), run.spans, starts, hard, dict(run.stats), date)
