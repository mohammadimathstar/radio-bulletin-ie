"""Settings and small data classes of the preprocessing."""
from __future__ import annotations

from dataclasses import dataclass, field

#: headers of a section of a bulletin (matched fuzzily, so BUITENIAND: is recognised and corrected)
HEADERS = ("BINNENLAND", "BUITENLAND", "WEERSVERWACHTING", "SPORT", "HONKBAL", "CRICKET", "VOETBAL", "ATHLETIEK", "WIELRIJDEN",
           "PAARDENSPORT", "ZWEMMEN", "SCHAKEN", "BEURSBERICHT")


@dataclass
class CleanConfig:
    unicode: bool = True                 # control characters, quotes, dashes, NFC; non-Latin scripts (Cyrillic, Greek...) removed
    metadata: str = "tag"                # broadcast metadata (telex references, schedule codes, ...): "tag" = keep in the text and list as spans, "remove" = also delete
    artifacts: bool = True               # stray number lines, xxx / *** fillers, "$word", archival references
    join_words: bool = True              # repair words split by a line break (needs a lexicon), de-hyphenation, doubled words at a line break
    digits_letters: bool = True          # I939 -> 1939, 0OSTDUITSCHLAND -> OOSTDUITSCHLAND
    punctuation: bool = True             # missing space after a period, a slash between letters, spaces before punctuation
    min_join_freq: int = 3               # the joined word must occur at least this often in the lexicon
    join_ratio: float = 10.0             # a fragment is a fragment if it is this many times rarer than the joined word
    headers: tuple[str, ...] = HEADERS
    header_cutoff: float = 0.82          # similarity needed to recognise a damaged header


@dataclass
class Span:
    """Something found in the text, in RAW offsets."""
    kind: str       # section_header | bulletin_header | telex_reference | schedule_code | copy_designation | continuation | broadcast_instruction | archival_reference | number_line | filler | ...
    start: int
    end: int
    text: str
    action: str     # kept | removed | fixed

    def to_dict(self) -> dict:
        return dict(kind=self.kind, start=self.start, end=self.end, text=self.text, action=self.action)
