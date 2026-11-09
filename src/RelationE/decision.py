"""
From JEV's probabilities to relations.

JEV answers a multiple-choice question: a probability for every option (every relation in every allowed direction, plus no_relation). The decision rule here works on RELATIONS,
not on single options: the probabilities of the two directions of the same relation are added (a model that is sure about "beat" but unsure about the direction should still output beat,
and the uncertainty is reported as direction_confidence).

    p_relation   = sum of the option probabilities of the best relation
    margin       = p_relation - p(no_relation)
    accepted if  p_relation >= min_probability  and  margin >= min_margin
Every pair keeps its probabilities in the output, so the thresholds can be chosen afterwards (evaluation/) without calling JEV again.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.util.names import mention_key
from src.configs.re_cfg import DecisionConfig

from .models import CandidatePair, Mention, PairPrediction
from .schema import COARSE_TO_CATEGORY, FINE_TO_COARSE, NO_RELATION



def relation_probabilities(pred: PairPrediction) -> dict[str, float]:
    """Probability per relation (directions added), no_relation excluded."""
    out: dict[str, float] = defaultdict(float)
    for option, p in pred.probabilities.items():
        info = pred.option_map.get(option)
        if info and info["relation"] != NO_RELATION:
            out[info["relation"]] += p
    return dict(out)


def levels_of(relation: str, level: str) -> tuple[str | None, str | None]:
    """(coarse, category) of a relation of the given schema level."""
    if level == "fine":
        coarse = FINE_TO_COARSE.get(relation)
        return coarse, COARSE_TO_CATEGORY.get(coarse) if coarse else None
    if level == "coarse":
        return relation, COARSE_TO_CATEGORY.get(relation)
    return None, relation


def _mention(m: Mention) -> dict[str, Any]:
    return dict(mention_id=m.mention_id, text=m.text, type=m.entity_type, start=m.start, end=m.end, normalized_name=m.normalized_name)


def decide(pred: PairPrediction, pair: CandidatePair, text: str, cfg: DecisionConfig | None = None, level: str = "fine") -> dict[str, Any] | None:
    """The relation record for a pair, or None if no relation is accepted."""
    cfg = cfg or DecisionConfig()
    rel_p = relation_probabilities(pred)
    if not rel_p:
        return None
    rel = max(rel_p, key=rel_p.get)
    p_rel, p_none = rel_p[rel], pred.probabilities.get(NO_RELATION, 0.0)
    if p_rel < cfg.min_probability or p_rel - p_none < cfg.min_margin:
        return None
    opts = {o: p for o, p in pred.probabilities.items() if pred.option_map.get(o, {}).get("relation") == rel}
    best = max(opts, key=opts.get)
    info = pred.option_map[best]
    by_id = {pair.entity1.mention_id: pair.entity1, pair.entity2.mention_id: pair.entity2}
    coarse, category = levels_of(rel, level)
    return dict(pair_id=pred.pair_id, relation=rel, coarse=coarse, category=category, head=_mention(by_id[info["head"]]), tail=_mention(by_id[info["tail"]]),
                probability=round(p_rel, 4), p_no_relation=round(p_none, 4), margin=round(p_rel - p_none, 4),
                direction_confidence=round(opts[best] / p_rel, 4) if p_rel else 0.0, selected_option=pred.selected_option, jev_confidence=round(pred.confidence, 4),
                evidence=dict(start=pair.context_start, end=pair.context_end, text=text[pair.context_start:pair.context_end]),
                sentence_ids=[pair.entity1.sentence_id, pair.entity2.sentence_id])


def merge_duplicate_relations(relations: list[dict[str, Any]], symmetric: set[str] | frozenset[str] = frozenset()) -> list[dict[str, Any]]:
    """One record per (relation, head entity, tail entity) where an entity is its type and normalized name: a relation stated for three mentions of 'VROLIJK' becomes one,
    with the best probability and the list of the mention pairs in `mention_pairs`. For knowledge-graph building; entity resolution across bulletins comes later."""
    groups: dict[tuple, list[dict[str, Any]]] = {}
    for r in relations:
        h = (r["head"]["type"], mention_key(Mention("", r["head"]["text"], r["head"]["type"], 0, 1, r["head"].get("normalized_name"))))
        t = (r["tail"]["type"], mention_key(Mention("", r["tail"]["text"], r["tail"]["type"], 0, 1, r["tail"].get("normalized_name"))))
        groups.setdefault((r["relation"], *(sorted((h, t)) if r["relation"] in symmetric else (h, t))), []).append(r)
    out = []
    for rs in groups.values():
        best = max(rs, key=lambda r: r["probability"])
        out.append(dict(best, n_mention_pairs=len(rs), mention_pairs=[[r["head"]["mention_id"], r["tail"]["mention_id"]] for r in rs]))
    return out
