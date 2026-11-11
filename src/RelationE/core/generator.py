
from collections import Counter

from ..dataLayer.models import Mention, CandidatePair, ContextGroup
from .sentences import context_boundaries, sentence_distance, character_distance
from ..dataLayer.schema import compatible_relations, FINE_RELATIONS, RelationDefinition, get_schema

from src.util.names import is_same_entity
from src.configs.re_cfg import CandidateConfig


# ---------------------------------------------------------
# Candidate generation
# ---------------------------------------------------------
def generate_candidates(mentions: list[Mention], 
                        text: str, 
                        spans: list[tuple[int, int]], 
                        schema: dict[str, RelationDefinition] | None = None,
                        cfg: CandidateConfig | None = None, stats: Counter | None = None
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
    cfg, schema = cfg or CandidateConfig(), schema or get_schema("fine")

    if cfg.max_sentence_distance < 0 or cfg.max_character_distance < 0:
        raise ValueError("distances cannot be negative")
    if not 0 <= cfg.similarity_threshold <= 1:
        raise ValueError("similarity_threshold must be between 0 and 1")

    stats = stats if stats is not None else Counter()
    ms = sorted(mentions, key=lambda m: (m.start, m.end))
    found: list[CandidatePair] = []
    for i, m1 in enumerate(ms):
        for m2 in ms[i + 1:]:
            if m2.start - m1.end > cfg.max_character_distance:
                break                                                   # sorted by start: every later mention is even farther away
            if m1.mention_id == m2.mention_id:
                stats["same_mention"] += 1
                continue
            if cfg.skip_nested_same_type and m1.entity_type == m2.entity_type and m2.start < m1.end:
                stats["nested_same_type"] += 1
                continue
            if is_same_entity(m1, m2, cfg):
                stats["same_entity"] += 1
                continue
            relations = compatible_relations(m1.entity_type, m2.entity_type, schema)
            if not relations:
                stats["no_compatible_relation"] += 1
                continue
            sd = sentence_distance(m1, m2)
            if sd is not None and sd > cfg.max_sentence_distance:
                stats["sentence_distance"] += 1
                continue

            cs, ce = context_boundaries(m1, m2, text, spans, cfg)
            found.append(CandidatePair("", m1, m2, relations, cs, ce, sd, character_distance(m1, m2)))
    
    if cfg.max_pairs is not None and len(found) > cfg.max_pairs:
        stats["max_pairs_cut"] += len(found) - cfg.max_pairs
        found = sorted(found, key=lambda p: (p.character_distance, p.entity1.start))[:cfg.max_pairs]
    found.sort(key=lambda p: (p.entity1.start, p.entity2.start, p.entity1.end, p.entity2.end))
    for n, p in enumerate(found, 1):
        p.pair_id = f"P{n:05d}"
    stats["candidate_pairs"] += len(found)
    return found



# ---------------------------------------------------------
# Group candidates by shared context
# ---------------------------------------------------------

def group_candidates(candidates: list[CandidatePair]) -> list[ContextGroup]:
    """
    Group pairs having identical context boundaries.

    Pairs from the same sentence will commonly share a context.
    This avoids repeating the same text in the JEV state.
    """
    groups: dict[tuple[int, int], list[CandidatePair]] = {}
    for c in candidates:
        groups.setdefault((c.context_start, c.context_end), []).append(c)
    return [ContextGroup(f"C{i:05d}", s, e, pairs) for i, ((s, e), pairs) in enumerate(sorted(groups.items()), 1)]




if __name__ == "__main__":
    import json
    from RelationE.core.sentences import sentence_spans, assign_sentence_ids

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
        spans=sent_spans,
        schema=FINE_RELATIONS,
        stats=None,
        cfg=cfg
    )

    for i, c in enumerate(candidates):
        # if i>10:
        #     break
        print("\n", c, "\n")
        print(text[c.context_start:c.context_end], "\n")

    # print(s)
        