import re
import unicodedata
import difflib

from src.RelationE.dataLayer.models import Mention
from src.configs.re_cfg import CandidateConfig

try:                                         # rapidfuzz is optional; difflib is the fallback
    from rapidfuzz import fuzz
except ImportError:                          # pragma: no cover
    fuzz = None

# ---------------------------------------------------------
# Name normalization
# ---------------------------------------------------------

TITLE_PREFIXES = ("den heer ", "de heer ", "mister ", "mevrouw ", "meneer ", "generaal ", "admiraal ", "kolonel ", "kapitein ", "minister ", "president ", "professor ",
                  "prof. ", "doctor ", "dr. ", "mr. ")


def normalize_name(name: str) -> str:
    """Lower case, no diacritics or punctuation, single spaces, common titles removed. The mention text itself is never changed."""
    name = unicodedata.normalize("NFKD", name.lower().strip())
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", name)).strip()
    changed = True
    while changed:
        changed = False
        for prefix in TITLE_PREFIXES:
            p = re.sub(r"[^\w\s]", "", prefix).strip() + " "
            if name.startswith(p):
                name, changed = name[len(p):].strip(), True
                break
    return name


def entity_similarity(name1: str, name2: str) -> float:
    """
    Calculate name similarity between two mentions.

    Uses:
    - WRatio: robust to partial names and spelling variation.
    - token_set_ratio: useful when one name contains only a surname
      while the other contains a full name.

    Returns a score between 0 and 1.
    """

    n1, n2 = normalize_name(name1), normalize_name(name2)
    if not n1 or not n2:
        return 0.0
    if n1 == n2:
        return 1.0

    if fuzz is not None:
        score1 = fuzz.WRatio(n1, n2)
        score2 = fuzz.token_set_ratio(n1, n2)
        return max(score1, score2) / 100.0
    return difflib.SequenceMatcher(None, n1, n2).ratio()


def mention_key(m: Mention) -> str:
    return normalize_name(m.normalized_name or m.text)


def is_same_entity(m1: Mention, m2: Mention, cfg: CandidateConfig) -> bool:
    """Different types are never the same entity. Equal names are. Short names must be equal; longer ones are compared fuzzily."""
    if m1.entity_type != m2.entity_type:
        return False
    k1, k2 = mention_key(m1), mention_key(m2)
    if k1 and k1 == k2:
        return True
    if min(len(k1), len(k2)) <= cfg.short_name_length:
        return False
    return max(entity_similarity(m1.text, m2.text), entity_similarity(k1, k2)) >= cfg.similarity_threshold
