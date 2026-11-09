import re
import unicodedata
from rapidfuzz import fuzz

from src.RelationE.models import Mention

# ---------------------------------------------------------
# Name normalization
# ---------------------------------------------------------

TITLE_PREFIXES = [
    "den heer ", "de heer ", "mister ", "mevrouw ", "meneer ", 
    "generaal ", "admiraal ", "kolonel ", "kapitein ",
    "minister ", "president ", "professor ", "prof. ", "doctor ", "dr. ", "mr. ",
]


def normalize_name(name):
    """
    Normalize a name for approximate string matching.

    The original mention text is never modified.

    This function:
    - Lowercases text.
    - Normalizes Unicode.
    - Removes diacritics.
    - Removes punctuation.
    - Removes common titles and honorifics.
    - Normalizes whitespace.
    """
    name = name.lower().strip()

    name = unicodedata.normalize("NFKD", name)
    name = "".join(
        c for c in name
        if not unicodedata.combining(c)
    )

    name = re.sub(r"[^\w\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    changed = True

    while changed:
        changed = False

        for prefix in TITLE_PREFIXES:
            if name.startswith(prefix):
                name = name[len(prefix):].strip()
                changed = True
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

    n1 = normalize_name(name1)
    n2 = normalize_name(name2)

    if not n1 or not n2:
        return 0.0

    if n1 == n2:
        return 1.0

    score1 = fuzz.WRatio(n1, n2)
    score2 = fuzz.token_set_ratio(n1, n2)

    return max(score1, score2) / 100.0


def is_same_entity(
    entity1: Mention,
    entity2: Mention,
    threshold: float,
) -> bool:
    """
    Binary duplicate decision.

    Different entity types are never considered duplicates.

    If the similarity reaches the threshold, the pair is discarded.
    There is no manual-review category.
    """

    if entity1.entity_type != entity2.entity_type:
        return False

    return (
        entity_similarity(entity1.text, entity2.text)
        >= threshold
    )