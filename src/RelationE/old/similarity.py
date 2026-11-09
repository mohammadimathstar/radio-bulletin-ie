import re
import unicodedata

from rapidfuzz import fuzz

from RelationE.old.models.models import Mention

TITLES = {
    "mister", "mr", "mrs", "miss",
    "mevrouw", "meneer", "heer",
    "den heer", "de heer",
    "generaal", "admiraal",
    "kolonel", "kapitein",
    "minister", "president",
}


def normalize_name(name: str) -> str:
    """
    Normalize a mention for approximate entity matching.

    This normalization is only used for comparison.
    It never modifies the original bulletin text.
    """

    name = name.lower().strip()

    name = unicodedata.normalize("NFKD", name)
    name = "".join(
        c for c in name
        if not unicodedata.combining(c)
    )

    name = re.sub(r"[^\w\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    tokens = [
        token for token in name.split()
        if token not in TITLES
    ]

    return " ".join(tokens)


def entity_similarity(name1: str, name2: str) -> float:
    """
    Return a similarity score between 0 and 1.

    Combines full-name similarity, token ordering,
    and individual token similarity.
    """

    n1 = normalize_name(name1)
    n2 = normalize_name(name2)

    if not n1 or not n2:
        return 0.0

    if n1 == n2:
        return 1.0

    scores = [
        fuzz.ratio(n1, n2),
        fuzz.token_sort_ratio(n1, n2),
        fuzz.WRatio(n1, n2),
    ]

    tokens1 = n1.split()
    tokens2 = n2.split()

    # Compare individual tokens to handle shortened names.
    token_scores = []

    for t1 in tokens1:
        for t2 in tokens2:
            # Avoid misleading matches on very short tokens.
            if min(len(t1), len(t2)) >= 4:
                token_scores.append(fuzz.ratio(t1, t2))

    if token_scores:
        scores.append(max(token_scores))

    return max(scores) / 100.0


def is_same_entity(
    entity1: Mention,
    entity2: Mention,
    threshold: float = 0.85,
) -> bool:
    """
    Automatically determine whether two mentions should
    be treated as mentions of the same entity.

    Only mentions with identical entity types are compared.

    No manual-review category is produced.
    """

    if entity1.entity_type != entity2.entity_type:
        return False

    return (
        entity_similarity(entity1.text, entity2.text)
        >= threshold
    )