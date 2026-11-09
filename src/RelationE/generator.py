from dataclasses import dataclass
import argparse
from itertools import combinations

from .models import Mention, CandidatePair, ContextGroup
from .sentences import get_context_boundaries, is_within_sentence_distance, get_character_distance
from .schema import compatible_relations, FINE_RELATIONS

from src.util.names import is_same_entity

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

    max_sentence_distance: int = 0
    max_character_distance: int = 500

    similarity_threshold: float = 0.85

    context_padding: int = 50




# ---------------------------------------------------------
# Candidate generation
# ---------------------------------------------------------

def generate_candidates(
    text: str,
    mentions: list[Mention],
    sent_spans: list[tuple[int, int]],
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

        # 3. Type compatibility. (TODO)
        relations = compatible_relations(
            entity1.entity_type,
            entity2.entity_type,
            FINE_RELATIONS
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
            sent_spans,
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



if __name__ == "__main__":
    import json
    from src.RelationE.sentences import sentence_spans, assign_sentence_ids

    with open('data/entity_annotations_raw.jsonl', 'r', encoding='utf-8') as f:
       lines = [json.loads(line) for line in f.readlines()]

    ids = 0
    text = lines[ids]['text']
    entities = lines[ids]['entities']

    sent_spans = sentence_spans(text)

    mentions = [Mention(i, ent['text'], ent['type'], ent['start'], ent['end']) for i, ent in enumerate(entities)]
    assign_sentence_ids(mentions, sent_spans)

    # parser = argparse.ArgumentParser()
    cfg = CandidateConfig()
    

    candidates = generate_candidates(
        text=text,
        mentions=mentions,
        sent_spans=sent_spans,
        config=cfg
    )

    for i, c in enumerate(candidates):
        # if i>10:
        #     break
        print("\n", c, "\n")
        print(text[c.context_start:c.context_end], "\n")
        