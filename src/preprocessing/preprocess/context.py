"""
Entity context extraction.

Given a cleaned ``CleanResult`` and a mention span (in EITHER cleaned or raw offsets),
return the sentence containing it, together with both the cleaned and raw offsets of the
sentence and of the mention. This is the helper your NER pipeline calls to get the
"sentence context" of an entity.

Why both offsets? Because:
  - the NER model runs on the CLEANED text, so its output is in cleaned offsets;
  - but the gold / original OCR is in raw offsets, so to compare against an annotation
    file you need to round-trip back to raw.

``CleanResult.aligned`` makes both directions O(log n).
"""
from __future__ import annotations

from dataclasses import dataclass

from .pipeline import CleanResult
from .sentences import split_sentences, Sentence


@dataclass(frozen=True)
class EntityContext:
    sentence_text: str
    sentence_clean_span: tuple[int, int]      # (start, end) in the CLEANED text
    sentence_raw_span: tuple[int, int]        # (start, end) in the RAW text
    entity_clean_span: tuple[int, int]        # (start, end) in the CLEANED text
    entity_raw_span: tuple[int, int]          # (start, end) in the RAW text
    entity_text: str                          # the cleaned text of the mention
    block_index: int                          # which block/item this sentence belongs to
    sentence_index: int                       # which sentence in the whole bulletin

    def to_dict(self) -> dict:
        return dict(
            sentence_text=self.sentence_text,
            sentence_clean_span=list(self.sentence_clean_span),
            sentence_raw_span=list(self.sentence_raw_span),
            entity_clean_span=list(self.entity_clean_span),
            entity_raw_span=list(self.entity_raw_span),
            entity_text=self.entity_text,
            block_index=self.block_index,
            sentence_index=self.sentence_index,
        )


def entity_context(
    res: CleanResult,
    start: int,
    end: int,
    span: str = "clean",
) -> EntityContext | None:
    """
    Return the sentence context of a mention.

    Parameters
    ----------
    res
        The ``CleanResult`` of the bulletin.
    start, end
        The mention span.
    span
        ``"clean"`` (default): ``start, end`` are offsets in ``res.text``.
        ``"raw"``:                ``start, end`` are offsets in the original OCR text.
                                  They are mapped to cleaned offsets via ``res.clean_span``;
                                  if the mention was entirely removed by cleaning, returns
                                  ``None``.
    """
    if span == "raw":
        cs = res.clean_span(start, end)
        if cs is None:
            return None
        c_start, c_end = cs
    elif span == "clean":
        c_start, c_end = start, end
    else:
        raise ValueError(f"span must be 'clean' or 'raw', got {span!r}")

    if not (0 <= c_start < c_end <= len(res.text)):
        return None

    # figure out which block this mention is in (block_starts are sorted cleaned offsets)
    block_index = 0
    for b in res.block_starts:
        if b <= c_start:
            block_index += 1
        else:
            break

    sentences = split_sentences(res)
    for i, s in enumerate(sentences):
        if s.start <= c_start and c_end <= s.end:
            rs, re_ = res.raw_span(s.start, s.end)
            ers, ere_ = res.raw_span(c_start, c_end)
            return EntityContext(
                sentence_text=s.text,
                sentence_clean_span=(s.start, s.end),
                sentence_raw_span=(rs, re_),
                entity_clean_span=(c_start, c_end),
                entity_raw_span=(ers, ere_),
                entity_text=res.text[c_start:c_end],
                block_index=block_index,
                sentence_index=i,
            )
    return None


def mentions_in_sentence(res: CleanResult, sent: Sentence) -> list[tuple[int, int]]:
    """Convenience: return the raw spans of every block of non-space text in a sentence.
    Useful as a poor-man's tokenizer when you want to enumerate candidate mentions
    without running a full NER model."""
    out: list[tuple[int, int]] = []
    i = sent.start
    while i < sent.end:
        while i < sent.end and res.text[i] == " ":
            i += 1
        if i >= sent.end:
            break
        j = i
        while j < sent.end and res.text[j] != " ":
            j += 1
        out.append(res.raw_span(i, j))
        i = j
    return out
