"""
The lexicon: word frequencies, used to decide whether two fragments form a word and whether a corrected word is real.

It is built from YOUR corpus (build_lexicon): words that occur at least `min_freq` times are words, OCR noise occurs once or twice. Frequencies, not
just membership, are what make the repairs safe: "DERLAND" is a fragment because it is 100 times rarer than "NEDERLAND", even if it occurs a few
times because the same split repeats. An optional external word list (e.g. OpenTaal) and a gazetteer of names (places, persons) add words with a high count.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Iterable

#: function words are never joined to a neighbour
STOPWORDS = frozenset("""de het een en van in op te aan bij met om tot uit voor naar over door als dat die dit zijn is was werd worden hebben heeft had niet ook nog
maar dan wel zal zullen kan kunnen moet moeten reeds tegen onder tusschen thans heden alle zich zij hij wij ik u er daar waar welke wordt""".split())
EXTERNAL_COUNT = 10_000
_TOKEN = re.compile(r"[^\W\d_]{2,}")


class Lexicon:
    def __init__(self, counts: dict[str, int] | None = None):
        self.counts: dict[str, int] = dict(counts or {})

    def freq(self, word: str) -> int:
        return self.counts.get(word.lower(), 0)

    def known(self, word: str, min_freq: int = 1) -> bool:
        return self.freq(word) >= min_freq

    def __len__(self) -> int:
        return len(self.counts)

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            for w, c in sorted(self.counts.items(), key=lambda kv: (-kv[1], kv[0])):
                fh.write(f"{w}\t{c}\n")

    @classmethod
    def load(cls, path: str | Path) -> "Lexicon":
        counts: dict[str, int] = {}
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                w, _, c = line.partition("\t")
                counts[w] = int(c or 1)
        return cls(counts)


def build_lexicon(texts: Iterable[str], cfg=None, min_freq: int = 3, wordlist: str | Path | None = None, gazetteer: str | Path | None = None) -> Lexicon:
    """Count the words of the (lightly cleaned) texts; keep those with at least min_freq occurrences; add the optional lists (one entry per line)."""
    from .config import CleanConfig
    from .pipeline import clean
    base = cfg or CleanConfig(join_words=False, digits_letters=False)
    counts: Counter = Counter()
    for t in texts:
        counts.update(w.lower() for w in _TOKEN.findall(clean(t, base).text))
    out = {w: c for w, c in counts.items() if c >= min_freq}
    for path in (wordlist, gazetteer):
        if path:
            for line in Path(path).read_text(encoding="utf-8").splitlines():
                w = line.strip().lower()
                if w and " " not in w:
                    out[w] = max(out.get(w, 0), EXTERNAL_COUNT)
    return Lexicon(out)
