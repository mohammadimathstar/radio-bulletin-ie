"""
The relation pipeline for one bulletin: sentences -> candidate pairs -> contexts -> JEV batches -> decisions.

    plan_bulletin     everything except the calls: how many pairs, batches and requests (a dry run)
    extract_bulletin  the whole thing; the record keeps the relations AND the probabilities of every pair, so thresholds can be tuned later without new calls
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Callable
from dataclasses import dataclass

from .generator import generate_candidates, group_candidates
from .decision import decide, merge_duplicate_relations
from .jev import ChoiceFactory, build_jev_batches, classify_all
from .models import Bulletin, CandidatePair, ContextGroup, JEVBatch
from .schema import NO_RELATION, get_schema
from .sentences import assign_sentence_ids, sentence_spans

from src.configs.re_cfg import PipelineConfig



def prepare(
        bulletin: Bulletin, 
        cfg: PipelineConfig, 
        choice_factory: ChoiceFactory | None = None,
        sentence_fn: Callable[[str], list[tuple[int, int]]] = sentence_spans) -> tuple[list[CandidatePair], list[ContextGroup], list[JEVBatch], Counter]:
    schema = get_schema(cfg.level)
    stats: Counter = Counter(bulletin.load_stats)
    spans = sentence_fn(bulletin.text)
    assign_sentence_ids(bulletin.mentions, spans)
    pairs = generate_candidates(bulletin.mentions, bulletin.text, spans, schema, cfg.candidate, stats)
    groups = group_candidates(pairs)
    batches = build_jev_batches(
        bulletin, groups, 
        schema, cfg.max_questions_per_request, 
        choice_factory, cfg.shared_instructions, cfg.compact_options)
    return pairs, groups, batches, stats


@dataclass
class PlainChoice:
    """Stand-in for typesafe_sdk.Choice in dry runs: no SDK needed to count pairs and requests."""
    instructions: str
    criteria: dict[str, str]

def plan_bulletin(bulletin: Bulletin, cfg: PipelineConfig, choice_factory: ChoiceFactory | None = None, sentence_fn=sentence_spans) -> dict[str, Any]:
    """Dry run: sizes without any JEV call."""
    pairs, groups, batches, stats = prepare(bulletin, cfg, choice_factory or PlainChoice, sentence_fn)
    by_types = Counter("-".join(sorted((p.entity1.entity_type, p.entity2.entity_type))) for p in pairs)
    # approx_chars = sum(len(str(b.state)) + sum(len(c.instructions) + sum(len(v) for v in c.criteria.values()) for c in b.questions.values()) for b in batches)
    
    approx_chars = sum(len(str(b.state)) + sum(_question_chars(q) for q in b.questions.values()) for b in batches)
    return dict(bulletin_id=bulletin.bulletin_id, 
                n_mentions=len(bulletin.mentions), 
                n_pairs=len(pairs), n_contexts=len(groups), 
                n_requests=len(batches),
                pairs_by_types=dict(by_types), 
                approx_request_chars=approx_chars, 
                stats=dict(stats))


# def _plain_choice(instructions: str, criteria: dict[str, str]) -> dict[str, Any]:
#     return {"instructions": instructions, "criteria": criteria}

def _question_chars(q: Any) -> int:
    instructions, criteria = (q["instructions"], q["criteria"]) if isinstance(q, dict) else (q.instructions, q.criteria)
    return len(instructions) + sum(len(v) for v in criteria.values())
 

def extract_bulletin(bulletin: Bulletin, 
                     client: Any, 
                     cfg: PipelineConfig | None = None, 
                     choice_factory: ChoiceFactory | None = None,
                     sentence_fn=sentence_spans, 
                     progress: bool = False) -> dict[str, Any]:
    cfg = cfg or PipelineConfig()
    pairs, _, batches, stats = prepare(bulletin, cfg, choice_factory, sentence_fn)
    predictions = classify_all(client, batches, cfg.model, cfg.retries, progress=progress) if batches else []
    by_id = {p.pair_id: p for p in pairs}
    relations = [r for pred in predictions if (r := decide(pred, by_id[pred.pair_id], bulletin.text, cfg.decision, cfg.level))]
    record: dict[str, Any] = dict(bulletin_id=bulletin.bulletin_id, 
                                  bulletin_date=bulletin.date, 
                                  schema_level=cfg.level,
                                  model=cfg.model, 
                                  n_mentions=len(bulletin.mentions),
                                  n_pairs=len(pairs), 
                                  n_requests=len(batches), 
                                  n_relations=len(relations), 
                                  relations=relations, stats=dict(stats))
    if cfg.merge_duplicates:

        schema = get_schema(cfg.level)
        record["relations_merged"] = merge_duplicate_relations(relations, {r for r, d in schema.items() if d.symmetric})
    
    if cfg.save_pairs:
        # print(predictions[0])
        record["pairs"] = [dict(pair_id=p.pair_id, entity1=p.entity1, entity2=p.entity2, selected_option=p.selected_option,
                                p_no_relation=round(p.probabilities.get(NO_RELATION, 0.0), 4),
                                top=[dict(option=o, p=round(v, 4)) for o, v in sorted(p.probabilities.items(), key=lambda kv: -kv[1])[:4]]) for p in predictions]
    return record
