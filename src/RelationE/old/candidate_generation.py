import re
import unicodedata

from dataclasses import dataclass
from itertools import combinations

from rapidfuzz import fuzz

from .models.models import Mention, CandidatePair, ContextGroup
from .models.schema_old import RELATION_SCHEMA


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

@dataclass
class CandidateConfig:
    """
    Configuration for candidate generation.

    max_sentence_distance:
        Maximum number of sentence boundaries between mentions.
        0 = same sentence only.
        1 = same or adjacent sentences.
        2 = up to two sentences apart.

    max_character_distance:
        Maximum number of characters separating the two mentions.

    similarity_threshold:
        If two mentions have the same type and their normalized
        name similarity reaches this threshold, the pair is excluded.

    context_padding:
        Number of additional characters included before and after
        the sentences containing the target mentions.
    """

    max_sentence_distance: int = 1
    max_character_distance: int = 200

    similarity_threshold: float = 0.85

    context_padding: int = 80


# ---------------------------------------------------------
# Name normalization
# ---------------------------------------------------------

TITLE_PREFIXES = [
    "den heer ",
    "de heer ",
    "mister ",
    "mevrouw ",
    "meneer ",
    "generaal ",
    "admiraal ",
    "kolonel ",
    "kapitein ",
    "minister ",
    "president ",
    "professor ",
    "prof. ",
    "doctor ",
    "dr. ",
    "mr. ",
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


# ---------------------------------------------------------
# Sentence segmentation
# ---------------------------------------------------------

def assign_sentence_ids(
    text: str,
    mentions: list[Mention],
    nlp,
) -> list[tuple[int, int]]:
    """
    Run spaCy sentence segmentation after NER.

    Assigns each mention to the sentence containing its midpoint.
    If the midpoint is not contained in a sentence, the sentence
    with the largest overlap is selected.

    Mentions without a reliable assignment retain sentence_id=None.
    Candidate generation will then rely on character proximity.

    Returns:
        List of (sentence_start, sentence_end) character offsets.
    """

    doc = nlp(text)

    try:
        sentences = list(doc.sents)
    except ValueError as exc:
        raise ValueError(
            "spaCy sentence boundaries are unavailable. "
            "Load a pipeline with a parser or sentencizer."
        ) from exc

    sentence_spans = [
        (sentence.start_char, sentence.end_char)
        for sentence in sentences
    ]

    for mention in mentions:

        midpoint = (mention.start + mention.end) // 2

        mention.sentence_id = None

        # First, try midpoint assignment.
        for sentence_id, (start, end) in enumerate(sentence_spans):

            if start <= midpoint < end:
                mention.sentence_id = sentence_id
                break

        # Fallback: choose the sentence with the largest overlap.
        if mention.sentence_id is None:

            overlaps = []

            for sentence_id, (start, end) in enumerate(sentence_spans):

                overlap = max(
                    0,
                    min(mention.end, end)
                    - max(mention.start, start),
                )

                overlaps.append((overlap, sentence_id))

            if overlaps:

                best_overlap, best_sentence = max(overlaps)

                if best_overlap > 0:
                    mention.sentence_id = best_sentence

    return sentence_spans


# ---------------------------------------------------------
# Relation compatibility
# ---------------------------------------------------------

def get_compatible_relations(
    type1: str,
    type2: str,
) -> list[str]:
    """
    Find relations compatible with two entity types.

    Textual order is not assumed to equal semantic direction.

    A relation is compatible if either entity ordering is allowed
    by its schema definition.
    """

    compatible = []

    for relation, definition in RELATION_SCHEMA.items():

        allowed = definition.allowed_types

        if (
            (type1, type2) in allowed
            or (type2, type1) in allowed
        ):
            compatible.append(relation)

    return compatible


# ---------------------------------------------------------
# Distance calculation
# ---------------------------------------------------------

def get_character_distance(
    entity1: Mention,
    entity2: Mention,
) -> int:
    """
    Return the number of characters between two mention spans.

    Returns zero if spans overlap.
    """

    left, right = sorted(
        [entity1, entity2],
        key=lambda entity: entity.start,
    )

    return max(0, right.start - left.end)


def is_within_sentence_distance(
    entity1: Mention,
    entity2: Mention,
    max_sentence_distance: int,
) -> bool:
    """
    Check sentence proximity.

    If either sentence assignment is unknown, return True and
    let character distance act as the fallback filter.
    """

    if (
        entity1.sentence_id is None
        or entity2.sentence_id is None
    ):
        return True

    distance = abs(
        entity1.sentence_id - entity2.sentence_id
    )

    return distance <= max_sentence_distance


# ---------------------------------------------------------
# Context extraction
# ---------------------------------------------------------

def get_context_boundaries(
    entity1: Mention,
    entity2: Mention,
    text: str,
    sentence_spans: list[tuple[int, int]],
    padding: int,
) -> tuple[int, int]:
    """
    Extract a context window covering the sentences containing
    both mentions.

    If sentence assignments are unavailable, use the mention
    spans directly.
    """

    if (
        entity1.sentence_id is not None
        and entity2.sentence_id is not None
    ):

        first = min(
            entity1.sentence_id,
            entity2.sentence_id,
        )

        last = max(
            entity1.sentence_id,
            entity2.sentence_id,
        )

        start = sentence_spans[first][0]
        end = sentence_spans[last][1]

    else:

        start = min(entity1.start, entity2.start)
        end = max(entity1.end, entity2.end)

    start = max(0, start - padding)
    end = min(len(text), end + padding)

    return start, end


# ---------------------------------------------------------
# Candidate generation
# ---------------------------------------------------------

def generate_candidates(
    text: str,
    mentions: list[Mention],
    sentence_spans: list[tuple[int, int]],
    config: CandidateConfig | None = None,
) -> list[CandidatePair]:
    """
    Generate candidate mention pairs.

    Filtering order:
        1. Exclude identical mention IDs.
        2. Exclude likely duplicate/same-entity mentions.
        3. Apply relation type compatibility.
        4. Apply sentence-distance filtering.
        5. Apply character-distance filtering.

    Each remaining pair receives a list of compatible relations.
    """

    if config is None:
        config = CandidateConfig()

    if config.max_sentence_distance < 0:
        raise ValueError("max_sentence_distance cannot be negative")

    if config.max_character_distance < 0:
        raise ValueError("max_character_distance cannot be negative")

    if not 0 <= config.similarity_threshold <= 1:
        raise ValueError("similarity_threshold must be between 0 and 1")

    # Preserve textual order.
    mentions = sorted(
        mentions,
        key=lambda entity: (entity.start, entity.end),
    )

    candidates = []

    pair_counter = 0

    for entity1, entity2 in combinations(mentions, 2):

        # 1. Never compare a mention with itself.
        if entity1.mention_id == entity2.mention_id:
            continue

        # 2. Exclude likely mentions of the same real-world entity.
        if is_same_entity(
            entity1,
            entity2,
            config.similarity_threshold,
        ):
            continue

        # 3. Type compatibility.
        relations = get_compatible_relations(
            entity1.entity_type,
            entity2.entity_type,
        )

        if not relations:
            continue

        # 4. Sentence distance.
        if not is_within_sentence_distance(
            entity1,
            entity2,
            config.max_sentence_distance,
        ):
            continue

        # 5. Character distance.
        distance = get_character_distance(
            entity1,
            entity2,
        )

        if distance > config.max_character_distance:
            continue

        # 6. Context boundaries.
        context_start, context_end = get_context_boundaries(
            entity1,
            entity2,
            text,
            sentence_spans,
            config.context_padding,
        )

        pair_counter += 1

        candidates.append(
            CandidatePair(
                pair_id=f"P{pair_counter:05d}",
                entity1=entity1,
                entity2=entity2,
                candidate_relations=relations,
                context_start=context_start,
                context_end=context_end,
            )
        )

    return candidates


# ---------------------------------------------------------
# Group candidates by shared context
# ---------------------------------------------------------

def group_candidates(
    candidates: list[CandidatePair],
) -> list[ContextGroup]:
    """
    Group pairs having identical context boundaries.

    Pairs from the same sentence will commonly share a context.
    This avoids repeating the same text in the JEV state.
    """

    groups = {}

    for candidate in candidates:

        key = (
            candidate.context_start,
            candidate.context_end,
        )

        if key not in groups:
            groups[key] = []

        groups[key].append(candidate)

    result = []

    for index, ((start, end), pairs) in enumerate(
        sorted(groups.items()),
        start=1,
    ):

        result.append(
            ContextGroup(
                context_id=f"C{index:05d}",
                context_start=start,
                context_end=end,
                pairs=pairs,
            )
        )

    return result
