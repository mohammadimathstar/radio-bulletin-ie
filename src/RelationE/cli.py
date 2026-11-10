"""
Command line: python -m relation_extraction {extract,plan,schema-check} ...

    plan          dry run: pairs, requests and sizes per bulletin, no JEV call
    extract       candidate pairs -> JEV -> relations, one JSON line per bulletin (resumable)
    schema-check  the entity types of the NER file against the schema; relations that can never fire

  python -m relation_extraction plan --input data/processed/ner.jsonl --limit 5
  python -m relation_extraction extract --input data/processed/ner.jsonl --out data/processed/relations.jsonl --min-probability 0.6
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

from .decision import DecisionConfig
from .io import done_ids, load_bulletins, type_counts
from .jev import ChoiceFactory, make_client
from .pipeline import extract_bulletin, plan_bulletin
from .schema import ALL_ENTITY_TYPES, check_entity_types, get_schema, validate_schema

from src.configs.re_cfg import CandidateConfig, PipelineConfig

load_dotenv()

def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--input", 
                #    required=True,
                   default='data/entity_annotations_raw.jsonl',
                   help="NER output: JSONL with bulletin_id, bulletin_date, text, entities")
    p.add_argument("--level", choices=["fine", "coarse", "category"], default="fine")
    p.add_argument("--limit", type=int, default=1)
    p.add_argument("--ids", help="a text file with one bulletin id per line")
    p.add_argument("--min-ner-confidence", type=float, default=0.0, help="drop mentions with a lower annotation_confidence")
    p.add_argument("--max-sentence-distance", type=int, default=0)
    p.add_argument("--max-character-distance", type=int, default=300)
    p.add_argument("--similarity-threshold", type=float, default=0.85)
    p.add_argument("--max-pairs", type=int, help="cap on the pairs per bulletin (nearest pairs are kept)")
    p.add_argument("--max-questions", type=int, default=30, help="questions per JEV request")
    p.add_argument("--no-shared-instructions", action="store_true", help="repeat the instructions in every question")
    p.add_argument("--compact-options", action="store_true", help="short option glosses; the full definitions once per request in the state (smaller requests)")


def _config(a: argparse.Namespace, **over: Any) -> PipelineConfig:
    cand = CandidateConfig(a.max_sentence_distance, a.max_character_distance, a.similarity_threshold, max_pairs=a.max_pairs)
    # return PipelineConfig(level=a.level, candidate=cand, max_questions_per_request=a.max_questions, shared_instructions=not a.no_shared_instructions, **over)
    return PipelineConfig(level=a.level, candidate=cand, max_questions_per_request=a.max_questions, shared_instructions=not a.no_shared_instructions, compact_options=a.compact_options, **over)


def _bulletins(a: argparse.Namespace):
    ids = set(Path(a.ids).read_text(encoding="utf-8").split()) if a.ids else None
    return load_bulletins(a.input, ALL_ENTITY_TYPES, a.min_ner_confidence, ids, a.limit)


def main(argv: list[str] | None = None, client: Any = None, choice_factory: ChoiceFactory | None = None) -> int:
    ap = argparse.ArgumentParser(prog="relation_extraction", description="Relation classification between NER mentions with JEV")
    sub = ap.add_subparsers(dest="cmd", required=True)
    plan = sub.add_parser("plan")
    _common(plan)
    ex = sub.add_parser("extract")
    _common(ex)
    ex.add_argument("--out", default="data/relations.jsonl")
    ex.add_argument("--model", default="jev-1.14.0")
    ex.add_argument("--min-probability", type=float, default=0.5, help="probability of the relation (both directions added) needed to accept it")
    ex.add_argument("--min-margin", type=float, default=0.0, help="the relation must beat no_relation by this much")
    ex.add_argument("--no-pairs", action="store_true", help="do not keep the probabilities of every pair in the output")
    ex.add_argument("--merge-duplicates", action="store_true", help="also write one record per entity pair (relations_merged)")
    ex.add_argument("--restart", action="store_true")
    sc = sub.add_parser("schema-check")
    sc.add_argument("--input", required=True)
    sc.add_argument("--level", choices=["fine", "coarse", "category"], default="fine")
    a = ap.parse_args(argv)

    if a.cmd == "schema-check":
        counts = type_counts(a.input)
        print("entity types in the data:", dict(counts))
        print(json.dumps(check_entity_types(counts, get_schema(a.level)), indent=1))
        print("schema problems:", validate_schema() or "none")
        return 0

    if a.cmd == "plan":
        total, pairs, by_types = Counter(), 0, Counter()
        for b in _bulletins(a):
            p = plan_bulletin(b, _config(a))
            print(f"{p['bulletin_id']}: {p['n_mentions']} mentions, {p['n_pairs']} pairs, {p['n_requests']} requests, ~{p['approx_request_chars']:,} characters")
            total.update(requests=p["n_requests"], pairs=p["n_pairs"], bulletins=1)
            by_types.update(p["pairs_by_types"])
        print(f"total: {dict(total)}; pairs by entity types: {dict(by_types.most_common())}")
        return 0

    out = Path(a.out)
    if a.restart and out.exists():
        out.unlink()
    skip = done_ids(out)
    cfg = _config(a, model=a.model, decision=DecisionConfig(a.min_probability, a.min_margin), save_pairs=not a.no_pairs, merge_duplicates=a.merge_duplicates)
    client = client or make_client()
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(out, "a", encoding="utf-8") as fh:
        for b in _bulletins(a):
            if b.bulletin_id in skip:
                continue
            rec = extract_bulletin(b, client, cfg, choice_factory)
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            n += 1
            print(f"{b.bulletin_id}: {rec['n_pairs']} pairs, {rec['n_requests']} requests, {rec['n_relations']} relations")
    print(f"{n} bulletins written to {out} ({len(skip)} were already done)")
    return 0


if __name__=='__main__':
    print('hi')
    main()

    # uv run python -m src.RelationE.cli extract