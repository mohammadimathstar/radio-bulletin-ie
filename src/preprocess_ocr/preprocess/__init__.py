"""
preprocess
==========

Preprocessing pipeline for the OCR'd Dutch radio bulletins (1938-1940 corpus).

Public API
----------
    from preprocess import clean, CleanConfig, CleanResult, Lexicon, build_lexicon
    from preprocess import split_sentences, entity_context, batch_clean

Pipeline (one text -> CleanResult):

    raw OCR text
        |
        v
    normalize_unicode   control chars, quotes/dashes, NFC; drop Cyrillic/Greek words; map homoglyphs
    tag_metadata        section headers (BUITENIAND: -> BUITENLAND:), bulletin header, telex refs,
                        schedule codes, copy designations, "(vervolg)", "Alleen VARA": kept as spans
    remove_artifacts    stray number lines (2, 68, 4c, C2), xxx / *** fillers, "$word", archival refs
    join_split_words    hyphenation, duplicated words at a break, fragments joined via a lexicon
    fix_digits_letters  I939 -> 1939, I4 April -> 14 April, II uur -> 11 uur, 0OSTDUITSCHLAND -> ...
    fix_punctuation     missing space after a period, slash between letters, space before punct
    flatten             every run of whitespace (line breaks included) -> ONE space; block starts kept

Design choices (deliberate)
---------------------------
* newlines are replaced by a single space at the end (flatten). Paragraph separation is NOT
  preserved as text layout, but the raw offsets where items/sections started are kept in
  ``CleanResult.block_starts`` (cleaned offsets), which is exactly what the sentence splitter
  needs to force a hard break at item boundaries.
* general letter-for-letter spelling correction (Category 2 noise, e.g. "venmiddag" -> "vanmiddag")
  is NOT done. It would require a Dutch spellchecker and would change named entities and compounds.
  The downstream entity pipeline already tolerates that via fuzzy matching.
* merging words split by a space (e.g. "vormook" -> "vorm ook") is NOT done automatically. It is
  high-risk for compounds; only line-break splits are joined, and only when the joined form is a
  known word that is much more frequent than the fragments.

See README at the bottom of this file for usage examples.
"""
from .alignment import AlignedText, Edit
from .config import CleanConfig, Span, HEADERS
from .lexicon import Lexicon, build_lexicon, STOPWORDS
from .pipeline import clean, CleanResult
from .sentences import split_sentences, Sentence, ABBREVIATIONS
from .context import entity_context, EntityContext


__all__ = [
    "AlignedText", "Edit",
    "CleanConfig", "Span", "HEADERS",
    "Lexicon", "build_lexicon", "STOPWORDS",
    "clean", "CleanResult",
    "split_sentences", "Sentence", "ABBREVIATIONS",
    "entity_context", "EntityContext",
    "batch_clean", "batch_clean_dir",
]


def __getattr__(name: str):
    """Lazy import of the CLI helpers so ``python -m preprocess.cli`` doesn't warn."""
    if name in ("batch_clean", "batch_clean_dir"):
        from ...preprocess import cli
        return getattr(cli, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

