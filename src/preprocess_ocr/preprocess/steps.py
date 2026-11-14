"""
The cleaning steps, in the order pipeline.clean applies them. Each takes an AlignedText and the RunState and returns a new AlignedText;
all of them work on the text WITH its line breaks, because line breaks carry information until the last step (flatten).

 1 normalize_unicode  control characters, quotes/dashes, NFC; words in other scripts (Cyrillic, Greek...) removed, homoglyphs inside Latin words mapped
 2 tag_metadata       section headers (BUITENIAND: -> BUITENLAND:), bulletin header, telex references, schedule codes, copy designations,
                      "(vervolg)", "Alleen VARA": listed as spans in raw offsets; kept in the text (metadata="tag") or deleted ("remove")
 3 remove_artifacts   stray number lines (2, 68, 4c, C2), xxx / *** fillers, "$word", archival references "( 5925/B)"; the place of a removed number line
                      is remembered as a block boundary (it usually separates two items)
 4 join_split_words   hyphenation at the end of a line, a word repeated at a line break, words split by a line break or a space (needs a lexicon)
 5 fix_digits_letters I939 -> 1939, "I4 April" -> "14 April", II uur -> 11 uur, 0OSTDUITSCHLAND -> OOSTDUITSCHLAND, 01ympisch -> Olympisch
 6 fix_punctuation    missing space after a period, a slash between letters, spaces before punctuation
 7 flatten            every run of whitespace (line breaks included) becomes ONE space; blank lines are remembered as block boundaries

What is deliberately NOT done: general spelling correction (letter-for-letter confusion such as "venmiddag") and splitting merged words. Both would
change names and compounds, and the entity pipeline already tolerates them through fuzzy matching.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from difflib import get_close_matches
from functools import lru_cache
from typing import Iterable

from .alignment import AlignedText, Edit
from .config import CleanConfig, Span
from .lexicon import STOPWORDS, Lexicon

MONTHS = "januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|october|november|december"
MONTH_NUMBER = {m: i for i, m in enumerate(["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september", "oktober", "november", "december"], 1)}
MONTH_NUMBER["october"] = 10


@dataclass
class RunState:
    cfg: CleanConfig
    lexicon: Lexicon | None = None
    spans: list[Span] = field(default_factory=list)
    stats: Counter = field(default_factory=Counter)
    boundaries: set[int] = field(default_factory=set)             # RAW offsets where a block (item, section) starts (layout info)
    sentence_breaks: set[int] = field(default_factory=set)        # subset of boundaries that are HARD sentence breaks
                                                                   #   (section_header, bulletin_header, blank_line)
                                                                   # removed number lines are boundaries but NOT sentence breaks

    def span(self, at: AlignedText, kind: str, start: int, end: int, action: str) -> None:
        rs, re_ = at.raw_span(start, end)
        self.spans.append(Span(kind, rs, re_, at.text[start:end], action))
        self.stats[f"{kind}:{action}"] += 1

    def boundary(self, at: AlignedText, pos: int, hard: bool = False) -> None:
        """Mark a layout boundary at ``pos`` (cleaned offset). If ``hard``, also force a sentence break here.

        Hard breaks: section headers, bulletin headers, blank lines.
        Soft breaks (layout only): removed number lines (``B2``, ``68``, ...) which may well have been
        mid-sentence OCR noise; the sentence splitter does NOT break at these.
        """
        if 0 <= pos < len(at.raw_index):
            rpos = at.raw_index[pos]
            self.boundaries.add(rpos)
            if hard:
                self.sentence_breaks.add(rpos)


def _non_overlapping(edits: Iterable[Edit]) -> list[Edit]:
    out: list[Edit] = []
    for e in sorted(edits, key=lambda e: (e.start, e.end)):
        if not out or e.start >= out[-1].end:
            out.append(e)
    return out


# ------------------------------------------------------------------ 1 unicode
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0e-\x1f\x7f\u200b-\u200f\u2028\u2029\ufeff]")
_CHARMAP = {"\u2018": "'", "\u2019": "'", "\u00b4": "'", "`": "'", "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u00ab": '"', "\u00bb": '"',
            "\u2013": "-", "\u2014": "-", "\u00a0": " ", "\x0c": "\n"}
_CHARS = re.compile("[" + re.escape("".join(_CHARMAP)) + "]")
_FOREIGN = {"CYRILLIC", "GREEK", "ARABIC", "HEBREW", "CJK", "HANGUL", "HIRAGANA", "KATAKANA", "THAI", "DEVANAGARI"}
CONFUSABLES = dict(zip("аеорсхуктіјАВЕКМНОРСТХ", "aeopcxyktijABEKMHOPCTX"))


@lru_cache(maxsize=None)
def _script(ch: str) -> str | None:
    return unicodedata.name(ch, "X").split(" ")[0] if ch.isalpha() else None


def normalize_unicode(at: AlignedText, run: RunState) -> AlignedText:
    text, edits = at.text, []
    for m in re.finditer(r"\r\n?", text):
        edits.append(Edit(m.start(), m.end(), "\n"))
    for m in _CONTROL.finditer(text):
        edits.append(Edit(m.start(), m.end()))
        run.stats["unicode:control"] += 1
    for m in _CHARS.finditer(text):
        edits.append(Edit(m.start(), m.end(), _CHARMAP[m.group()]))
    for m in re.finditer(r"[^\W\d_][\u0300-\u036f]+", text):
        edits.append(Edit(m.start(), m.end(), unicodedata.normalize("NFC", m.group())))
    for m in re.finditer(r"\S+", text):
        tok = m.group()
        if not any(_script(c) in _FOREIGN for c in tok):
            continue
        if any(_script(c) == "LATIN" for c in tok):                      # a Latin word with a look-alike letter: map it, drop the rest
            keep = [(m.start() + i, CONFUSABLES.get(c, c)) for i, c in enumerate(tok) if _script(CONFUSABLES.get(c, c)) not in _FOREIGN]
            edits.append(Edit(m.start(), m.end(), "".join(c for _, c in keep), tuple(i for i, _ in keep)))
            run.stats["unicode:homoglyph_word"] += 1
        else:                                                           # a word in another script: noise
            edits.append(Edit(m.start(), m.end()))
            run.stats["unicode:foreign_script_removed"] += 1
    return at.apply(_non_overlapping(edits))


# ------------------------------------------------------------------ 2 metadata
METADATA = (
    ("telex_reference", re.compile(r"\(\s*zie\s+telex[^)\n]{0,40}\)", re.I)),
    ("schedule_code", re.compile(r"\(\s*\d+e\s+(?:uitz\.?\s+)?\d{1,2}\s*,\s*(?:--|\d{2})\s*\)", re.I)),
    ("copy_designation", re.compile(r"\bCopie\s+[A-Z]{4,12}\b")),
    ("continuation", re.compile(r"\(\s*vervolg\s*\)", re.I)),
    ("broadcast_instruction", re.compile(r"\bAlleen\s+(?:VARA|KRO|NCRV|AVRO|VPRO|NRV)\b'?")),
)
_HEADER = re.compile(r"(?m)^([ \t]*)([A-Z]{5,14})([ \t]*:)")
_BULLETIN_HEADER = re.compile(rf"(?m)^[ \t]*(?:RADIO\b[^\n]{{0,80}}|[0-9IlO|]{{1,2}}[ \t]+(?i:{MONTHS})[ \t]+[0-9IlO|]{{4}}\.?)[ \t]*$")


def tag_metadata(at: AlignedText, run: RunState) -> AlignedText:
    text, edits, remove = at.text, [], run.cfg.metadata == "remove"
    for m in _HEADER.finditer(text):
        word = m.group(2)
        canon = get_close_matches(word, run.cfg.headers, 1, run.cfg.header_cutoff)
        if not canon:
            continue
        run.boundary(at, m.start(), hard=True)              # section headers always start a new sentence
        if canon[0] != word:
            edits.append(Edit(m.start(2), m.end(2), canon[0]))
            run.stats["header_fixed"] += 1
        run.span(at, "section_header", m.start(2), m.end(3), "fixed" if canon[0] != word else "kept")
    for m in _BULLETIN_HEADER.finditer(text, 0, 300):
        run.span(at, "bulletin_header", m.start(), m.end(), "kept")
        run.boundary(at, m.start(), hard=True)               # bulletin header starts a new sentence
        run.boundary(at, m.end() + 1, hard=True)             # ...and so does the line after it
    for kind, pat in METADATA:
        for m in pat.finditer(text):
            run.span(at, kind, m.start(), m.end(), "removed" if remove else "kept")
            if remove:
                edits.append(Edit(m.start(), m.end()))
    return at.apply(_non_overlapping(edits))


# ------------------------------------------------------------------ 3 artifacts
_NUMBER_LINE = re.compile(r"(?m)^[ \t]*(?:\d{1,3}[A-Za-z\u00aa]?|[A-Za-z]\d{1,2})[ \t]*(?:\n|\Z)")
_FILLER = re.compile(r"(?<!\w)(?:x{3,}|\*{2,})(?!\w)")
_DOLLAR = re.compile(r"\$(?=[^\W\d_])")
_ARCHIVAL = re.compile(r"\(\s*\d{3,5}\s*/?\s*[A-Za-z]{1,3}\s*\)")


def remove_artifacts(at: AlignedText, run: RunState) -> AlignedText:
    text, edits = at.text, []
    for m in _NUMBER_LINE.finditer(text):
        run.span(at, "number_line", m.start(), m.end(), "removed")
        run.boundary(at, m.end(), hard=False)                # layout boundary only; NOT a sentence break
                                                              # (a removed number line is often mid-sentence OCR noise)
        edits.append(Edit(m.start(), m.end()))
    for kind, pat in (("filler", _FILLER), ("archival_reference", _ARCHIVAL)):
        for m in pat.finditer(text):
            run.span(at, kind, m.start(), m.end(), "removed")
            edits.append(Edit(m.start(), m.end()))
    for m in _DOLLAR.finditer(text):
        run.stats["artifact:dollar"] += 1
        edits.append(Edit(m.start(), m.end()))
    return at.apply(_non_overlapping(edits))


# ------------------------------------------------------------------ 4 split words
def _gap_kind(gap: str) -> str | None:
    if re.fullmatch(r"[ \t]+", gap):
        return "space"
    if re.fullmatch(r"[ \t]*\n[ \t]*", gap):
        return "break"
    if re.fullmatch(r"[ \t]+\d{1,2}[ \t]*\n[ \t]*|[ \t]+\d{1,2}[ \t]+", gap):          # a page/item number injected into the word
        return "number"
    return None


def _may_join(lex: Lexicon, a: str, b: str, kind: str, cfg: CleanConfig) -> bool:
    """Join two fragments if the result is a known word and the fragments are rare compared to it (both for a space, one for a line break)."""
    la, lb = a.lower(), b.lower()
    if la in STOPWORDS or lb in STOPWORDS or len(la) + len(lb) < 6:
        return False
    f_ab = lex.freq(la + lb)
    if f_ab < cfg.min_join_freq:
        return False
    rare = lambda w: lex.freq(w) * cfg.join_ratio < f_ab
    return (rare(la) and rare(lb)) if kind == "space" else (rare(la) or rare(lb))


def join_split_words(at: AlignedText, run: RunState) -> AlignedText:
    lex = run.lexicon
    # a) hyphenation at the end of a line: join if the result is a word (ver-\nvolgens), else keep the hyphen (Noord-\nHolland)
    edits = []
    for m in re.finditer(r"([^\W\d_]{2,})-[ \t]*\n[ \t]*([^\W\d_]{2,})", at.text):
        a, b = m.group(1), m.group(2)
        word = lex is not None and lex.known((a + b).lower(), run.cfg.min_join_freq)
        src = tuple(range(m.start(1), m.end(1))) + (() if word else (m.end(1),)) + tuple(range(m.start(2), m.end(2)))
        edits.append(Edit(m.start(), m.end(), a + b if word else a + "-" + b, src))
        run.stats["dehyphenated" if word else "hyphen_kept"] += 1
    at = at.apply(edits)
    # b) a word repeated at a line break (DANTZIG\nDANTZIG)
    edits = []
    for m in re.finditer(r"(?i)\b([^\W\d_]{4,})[ \t]*\n[ \t]*\1\b", at.text):
        edits.append(Edit(m.start(), m.end(), m.group(1), tuple(range(m.start(1), m.end(1)))))
        run.stats["duplicate_word"] += 1
    at = at.apply(edits)
    # c) fragments of a word (AMSTER\nDAM, GRO NINGEN, FIN 12\nLAND): needs a lexicon
    if lex is None:
        return at
    text, edits = at.text, []
    toks = list(re.finditer(r"[^\W\d_]+", text))
    i = 0
    while i < len(toks):
        cur, members, j = toks[i].group(), [toks[i]], i
        while j + 1 < len(toks):
            kind = _gap_kind(text[toks[j].end():toks[j + 1].start()])
            if kind is None or not _may_join(lex, cur, toks[j + 1].group(), kind, run.cfg):
                break
            cur += toks[j + 1].group()
            members.append(toks[j + 1])
            j += 1
        if len(members) > 1:
            edits.append(Edit(members[0].start(), members[-1].end(), cur, tuple(k for t in members for k in range(t.start(), t.end()))))
            run.stats["joined_words"] += 1
        i = j + 1
    return at.apply(edits)


# ------------------------------------------------------------------ 5 digits and letters
_NUMERAL = str.maketrans({"I": "1", "l": "1", "|": "1", "O": "0"})
_DATE_NUMERALS = re.compile(rf"\b([0-9IlO|]{{1,2}})([ \t]+(?i:{MONTHS})[ \t]+)([0-9IlO|]{{4}})\b")
_NUMERIC_TOKEN = re.compile(r"(?<![\w/.-])(?=[0-9IlO|]*\d)(?=[0-9IlO|]*[IlO|])[0-9IlO|]{2,5}(?![\w/.-])")
_HOUR = re.compile(r"\b([Il|]{1,2})(?=[ \t]*uur\b)")
_MIXED_WORD = re.compile(r"\b(?=[^\W_]*\d)(?=[^\W_]*[^\W\d_])[^\W_]{4,}\b")


def fix_digits_letters(at: AlignedText, run: RunState) -> AlignedText:
    text, edits, covered = at.text, [], []
    overlaps = lambda s, e: any(s < ce and cs < e for cs, ce in covered)

    def add(s: int, e: int, new: str, stat: str) -> None:
        if new != text[s:e] and not overlaps(s, e):
            edits.append(Edit(s, e, new))
            covered.append((s, e))
            run.stats[stat] += 1

    for m in _DATE_NUMERALS.finditer(text):                              # "I4 April I939" -> "14 April 1939" (the month tells that these are numbers)
        for g in (1, 3):
            add(m.start(g), m.end(g), m.group(g).translate(_NUMERAL), "digit_fix:date")
    for m in _HOUR.finditer(text):                                       # "II uur" -> "11 uur"
        add(m.start(), m.end(), m.group(1).translate(_NUMERAL), "digit_fix:hour")
    for m in _NUMERIC_TOKEN.finditer(text):                              # a token of digits and I/l/O: a number
        add(m.start(), m.end(), m.group().translate(_NUMERAL), "digit_fix:number")
    lex = run.lexicon
    for m in _MIXED_WORD.finditer(text):                                 # letters with 0/1/5 inside: 01ympisch, 0OSTDUITSCHLAND
        tok = m.group()
        if sum(c.isalpha() for c in tok) < 3 or tok[-1].isdigit() or re.fullmatch(r"\d+(?:ste|de|e)", tok) or set(re.sub(r"\D", "", tok)) - set("015"):
            continue
        upper = all(c.isupper() for c in tok if c.isalpha())
        new = "".join({"0": "O" if upper or i == 0 else "o", "1": "I" if upper or i == 0 else "l", "5": "S" if upper or i == 0 else "s"}.get(c, c)
                      for i, c in enumerate(tok))
        if (lex is not None and lex.known(new.lower())) or (lex is None and sum(c.isalpha() for c in tok) >= 4):
            add(m.start(), m.end(), new, "digit_fix:word")
    return at.apply(edits)


# ------------------------------------------------------------------ 6 punctuation
def fix_punctuation(at: AlignedText, run: RunState) -> AlignedText:
    text, edits = at.text, []
    for m in re.finditer(r"(?<=[a-z]{2})\.(?=[A-Z][a-z])", text):          # "gegaan.Ofschoon" -> "gegaan. Ofschoon" (N.V., z.g. are not matched)
        edits.append(Edit(m.end(), m.end(), " "))
        run.stats["punct:space_after_period"] += 1
    for m in re.finditer(r"(?<=[A-Za-z])/(?=[A-Za-z])", text):             # "spoorwegen/in"; fractions such as 7/8 are not touched
        edits.append(Edit(m.start(), m.end(), " "))
        run.stats["punct:slash"] += 1
    for m in re.finditer(r"[ \t]+(?=[,;:!?)])|(?<=\()[ \t]+", text):       # "week , waren" and "( slotkoers 32 )"
        edits.append(Edit(m.start(), m.end()))
        run.stats["punct:space"] += 1
    return at.apply(_non_overlapping(edits))


# ------------------------------------------------------------------ 7 flatten
# def flatten(at: AlignedText, run: RunState) -> AlignedText:
#     text, edits = at.text, []
#     for m in re.finditer(r"\n[ \t]*\n", text):                            # a blank line: a new block AND a hard sentence break
#         run.boundary(at, m.end(), hard=True)
#     for m in re.finditer(r"\s+", text):
#         if m.group() != " ":
#             edits.append(Edit(m.start(), m.end(), "" if m.start() == 0 or m.end() == len(text) else " "))
#     run.stats["newlines_flattened"] += text.count("\n")
#     return at.apply(edits)

def flatten(at: AlignedText, run: RunState) -> AlignedText:
    """Spaces/tabs and SINGLE line breaks become one space, but blank lines (paragraph
    separators) are KEPT: a whitespace run containing 2+ newlines survives as exactly
    '\n\n' and stays a block boundary + hard sentence break."""
    text, edits = at.text, []
    for m in re.finditer(r"\s+", text):
        edge = m.start() == 0 or m.end() == len(text)
        if m.group().count("\n") >= 2 and not edge:                        # a blank line: a paragraph separator
            run.boundary(at, m.end(), hard=True)                           # a new block AND a hard sentence break
            if m.group() != "\n\n":                                        # '\n \n', '\n\n\n', ... -> exactly '\n\n'
                edits.append(Edit(m.start(), m.end(), "\n\n", (m.start(), m.start() + 1)))
            run.stats["paragraph_breaks_kept"] += 1
        elif m.group() != " ":                                             # single line break / run of spaces -> ONE space
            run.stats["newlines_flattened"] += m.group().count("\n")
            edits.append(Edit(m.start(), m.end(), "" if edge else " "))
    return at.apply(edits)