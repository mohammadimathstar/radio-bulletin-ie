"""
refine.py - re-run only the bulletins that came out with too few relations, with wider candidate settings, and only for the pairs that were NOT decided before.

    python -m relation_extraction.refine --previous data/relations.jsonl --input data/entity_annotations_raw.jsonl --out data/relations_refined.jsonl \
        --min-relations 1 --max-sentence-distance 1 --max-character-distance 300

What it does
  1. reads the previous output and selects the bulletins with n_relations < --min-relations (and, with --include-missing, bulletins of the NER file that are not in it);
  2. for each of them generates the candidate pairs with the NEW settings (e.g. a larger --max-sentence-distance);
  3. drops every pair that the previous run already decided. A pair is identified by its two NER mention ids (entity1, entity2: stable and always in text order); pair_ids are
     NOT used because they are renumbered in every run. Decisions (including no_relation) are read from the `pairs` list of the previous record, so that run must not have used --no-pairs;
  4. sends only the new pairs to JEV (new pair_ids continue the numbering of the old ones);
  5. writes ONE combined output: untouched bulletins are copied as they are, refined bulletins get old + new `relations`, `pairs`, counts, and a `refinement` log entry with the
     settings and the numbers of this round. The output of a round can be the `--previous` of the next round.
Only the settings that widen the candidate set (max-sentence-distance, max-character-distance, max-pairs) can be changed safely: the old decisions were made on contexts built with the old
padding / context limits, and the thresholds (--min-probability, --min-margin) apply to the NEW pairs only (old decisions are kept as they are).

--dry-run prints which bulletins would be refined and how many new pairs, requests and characters that means, without any JEV call. The output file is written bulletin by bulletin, so an interrupted
run continues where it stopped (run again with the same --out); --restart starts the output again.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:                                  # pragma: no cover
    pass

                                               # the project layout of the uploaded cli.py ...
from src.configs.re_cfg import CandidateConfig, PipelineConfig

from .core.generator import generate_candidates, group_candidates
from .core.decision import DecisionConfig, decide, merge_duplicate_relations
from .dataLayer.io import load_bulletins
from .core.jev import ChoiceFactory, build_jev_batches, classify_all, make_client
from .dataLayer.models import Bulletin
from .dataLayer.schema import ALL_ENTITY_TYPES, NO_RELATION, get_schema
from .core.sentences import assign_sentence_ids, sentence_spans

PairKey = tuple[str, str]


@dataclass
class _PlainChoice:
    """Stand-in for typesafe_sdk.Choice in a dry run."""
    instructions: str
    criteria: dict[str, str]


# ------------------------------------------------------------------ the previous output
def read_records(path: str | Path) -> list[dict[str, Any]]:
    """Records of an output file in the order of first appearance; if a bulletin occurs twice the last record wins."""
    order: list[str] = []
    by_id: dict[str, dict[str, Any]] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rec = json.loads(line)
                if rec["bulletin_id"] not in by_id:
                    order.append(rec["bulletin_id"])
                by_id[rec["bulletin_id"]] = rec
    return [by_id[i] for i in order]


def count_relations(rec: dict[str, Any]) -> int:
    return rec.get("n_relations", len(rec.get("relations", [])))


def needs_refinement(rec: dict[str, Any], min_relations: int) -> bool:
    return count_relations(rec) < min_relations


def decided_pairs(rec: dict[str, Any]) -> set[PairKey] | None:
    """The pairs the previous run decided (relation or no_relation), as (entity1, entity2) NER ids; None if the record has no `pairs` list (run with --no-pairs)."""
    if "pairs" not in rec:
        return None
    return {(p["entity1"], p["entity2"]) for p in rec["pairs"]}


def _max_pair_number(rec: dict[str, Any]) -> int:
    ids = [p["pair_id"] for p in rec.get("pairs", [])] + [r["pair_id"] for r in rec.get("relations", [])]
    return max((int(m.group(1)) for i in ids if (m := re.fullmatch(r"P(\d+)", i))), default=0)


# ------------------------------------------------------------------ one bulletin
def _candidate_settings(cfg: Any) -> dict[str, Any]:
    c = cfg.candidate
    return {k: getattr(c, k, None) for k in ("max_sentence_distance", "max_character_distance", "similarity_threshold", "max_pairs")}


def new_pairs_for(bulletin: Bulletin, previous: dict[str, Any] | None, cfg: Any, stats: Counter) -> list[Any]:
    """Candidate pairs of the NEW settings that were not decided before, numbered after the old ones."""
    schema = get_schema(cfg.level)
    spans = sentence_spans(bulletin.text)
    assign_sentence_ids(bulletin.mentions, spans)
    pairs = generate_candidates(bulletin.mentions, bulletin.text, spans, schema, cfg.candidate, stats)
    decided = decided_pairs(previous) if previous else set()
    keep = [p for p in pairs if (p.entity1.mention_id, p.entity2.mention_id) not in (decided or set())]
    stats["skipped_already_decided"] += len(pairs) - len(keep)
    start = _max_pair_number(previous) + 1 if previous else 1
    for n, p in enumerate(keep, start):
        p.pair_id = f"P{n:05d}"
    return keep


def refine_bulletin(bulletin: Bulletin, previous: dict[str, Any] | None, client: Any, cfg: Any, choice_factory: ChoiceFactory | None = None,
                    min_relations: int = 1) -> tuple[dict[str, Any], dict[str, Any]]:
    """(record, info). previous=None runs the bulletin from scratch. If the previous record has no `pairs` list it is replaced by a full new run (its relations could not be
    told apart from the new ones). info reports what was new."""
    stats: Counter = Counter()
    replaced = previous is not None and decided_pairs(previous) is None
    base = None if replaced else previous
    pairs = new_pairs_for(bulletin, base, cfg, stats)
    by_id = {p.pair_id: p for p in pairs}
    batches = build_jev_batches(bulletin, group_candidates(pairs), get_schema(cfg.level), cfg.max_questions_per_request, choice_factory, cfg.shared_instructions,
                                cfg.compact_options) if pairs else []
    predictions = classify_all(client, batches, cfg.model, getattr(cfg, "retries", 2)) if batches else []
    new_relations = [r for pred in predictions if (r := decide(pred, by_id[pred.pair_id], bulletin.text, cfg.decision, cfg.level))]
    new_pair_records = [dict(pair_id=p.pair_id, entity1=p.entity1, entity2=p.entity2, selected_option=p.selected_option,
                             p_no_relation=round(p.probabilities.get(NO_RELATION, 0.0), 4),
                             top=[dict(option=o, p=round(v, 4)) for o, v in sorted(p.probabilities.items(), key=lambda kv: -kv[1])[:4]]) for p in predictions]
    log = dict(settings=_candidate_settings(cfg), min_relations=min_relations, new_pairs=len(pairs), skipped_already_decided=stats["skipped_already_decided"],
               requests=len(batches), new_relations=len(new_relations), candidate_stats=dict(stats), replaced_previous=replaced)
    if base is None:                                                      # a new record
        rec: dict[str, Any] = dict(bulletin_id=bulletin.bulletin_id, bulletin_date=bulletin.date, schema_level=cfg.level, n_mentions=len(bulletin.mentions),
                                   n_pairs=0, n_requests=0, n_relations=0, relations=[], stats=dict(bulletin.load_stats), pairs=[])
    else:
        rec = json.loads(json.dumps(base))                                # a copy
        rec.setdefault("pairs", [])
    rec["relations"] = rec["relations"] + new_relations
    rec["pairs"] = rec["pairs"] + new_pair_records
    rec["n_pairs"], rec["n_requests"], rec["n_relations"] = len(rec["pairs"]), rec.get("n_requests", 0) + len(batches), len(rec["relations"])
    rec["refinement"] = rec.get("refinement", []) + [log]
    if "relations_merged" in rec or getattr(cfg, "merge_duplicates", False):
        schema = get_schema(cfg.level)
        rec["relations_merged"] = merge_duplicate_relations(rec["relations"], {r for r, d in schema.items() if d.symmetric})
    return rec, dict(new_pairs=len(pairs), skipped=stats["skipped_already_decided"], requests=len(batches), new_relations=len(new_relations), replaced=replaced)


def plan_refinement(bulletin: Bulletin, previous: dict[str, Any] | None, cfg: Any) -> dict[str, Any]:
    """Dry run for one bulletin: the new pairs and the size of the requests, without any call."""
    stats: Counter = Counter()
    replaced = previous is not None and decided_pairs(previous) is None
    pairs = new_pairs_for(bulletin, None if replaced else previous, cfg, stats)
    batches = build_jev_batches(bulletin, group_candidates(pairs), get_schema(cfg.level), cfg.max_questions_per_request, _PlainChoice, cfg.shared_instructions,
                                cfg.compact_options) if pairs else []
    chars = sum(len(str(b.state)) + sum(len(q.instructions) + sum(len(v) for v in q.criteria.values()) for q in b.questions.values()) for b in batches)
    return dict(new_pairs=len(pairs), skipped=stats["skipped_already_decided"], requests=len(batches), approx_chars=chars, replaced=replaced)


# ------------------------------------------------------------------ command line
def _args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="refine", description="Re-run bulletins with too few relations, with wider candidate settings, for the undecided pairs only")
    p.add_argument("--input", default="data/entity_annotations_raw.jsonl", help="NER output (JSONL)")
    p.add_argument("--previous", default="data/relations.jsonl", help="the output of the previous run (it must contain the `pairs` lists)")
    p.add_argument("--out", default="data/relations_refined.jsonl", help="combined output: untouched + refined bulletins")
    p.add_argument("--min-relations", type=int, default=1, help="bulletins with fewer relations than this are re-run")
    g = p.add_argument_group("new candidate settings")
    g.add_argument("--max-sentence-distance", type=int, default=1)
    g.add_argument("--max-character-distance", type=int, default=300)
    g.add_argument("--similarity-threshold", type=float, default=0.85)
    g.add_argument("--max-pairs", type=int)
    g = p.add_argument_group("as in cli.py")
    g.add_argument("--level", choices=["fine", "coarse", "category"], default="fine", help="must be the level of the previous run")
    g.add_argument("--max-questions", type=int, default=30)
    g.add_argument("--no-shared-instructions", action="store_true")
    g.add_argument("--compact-options", action="store_true")
    g.add_argument("--model", default="jev-1.14.0")
    g.add_argument("--min-probability", type=float, default=0.5)
    g.add_argument("--min-margin", type=float, default=0.0)
    g.add_argument("--merge-duplicates", action="store_true")
    g.add_argument("--min-ner-confidence", type=float, default=0.0)
    g = p.add_argument_group("selection and control")
    g.add_argument("--ids", help="a text file with bulletin ids: refine only these (if they are below the threshold)")
    g.add_argument("--limit", type=int, help="refine at most this many bulletins (the others are copied unchanged)")
    g.add_argument("--include-missing", action="store_true", help="also run bulletins of the NER file that are not in the previous output")
    g.add_argument("--dry-run", action="store_true", help="only report what would be done")
    g.add_argument("--restart", action="store_true", help="start the output file again (default: continue an interrupted run)")
    g.add_argument("--report", help="write a JSON report with the numbers per bulletin")
    return p.parse_args(argv)


def _config(a: argparse.Namespace) -> Any:
    cand = CandidateConfig(max_sentence_distance=a.max_sentence_distance, max_character_distance=a.max_character_distance, similarity_threshold=a.similarity_threshold, max_pairs=a.max_pairs)
    return PipelineConfig(level=a.level, candidate=cand, max_questions_per_request=a.max_questions, shared_instructions=not a.no_shared_instructions, compact_options=a.compact_options,
                          model=a.model, decision=DecisionConfig(a.min_probability, a.min_margin), merge_duplicates=a.merge_duplicates)


def _done_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with open(path, encoding="utf-8") as fh:
        return {json.loads(l)["bulletin_id"] for l in fh if l.strip()}


def main(argv: list[str] | None = None, client: Any = None, choice_factory: ChoiceFactory | None = None) -> int:
    a = _args(argv)
    cfg = _config(a)
    previous = read_records(a.previous)
    wanted = set(Path(a.ids).read_text(encoding="utf-8").split()) if a.ids else None
    targets = [r for r in previous if needs_refinement(r, a.min_relations) and (wanted is None or r["bulletin_id"] in wanted)]
    bad_level = [r["bulletin_id"] for r in targets if r.get("schema_level", a.level) != a.level]
    if bad_level:
        raise SystemExit(f"--level {a.level} differs from the schema level of the previous run ({previous[0].get('schema_level')}) for {len(bad_level)} bulletins: the options cannot be mixed")
    in_previous = {r["bulletin_id"] for r in previous}
    with open(a.input, encoding="utf-8") as fh:
        ner_ids = [json.loads(l)["bulletin_id"] for l in fh if l.strip()]
    missing = [i for i in ner_ids if i not in in_previous and (wanted is None or i in wanted)]
    if a.limit:
        targets = targets[: a.limit]
    target_ids = [r["bulletin_id"] for r in targets] + (missing if a.include_missing else [])
    if a.limit and a.include_missing:
        target_ids = target_ids[: a.limit]
    print(f"{len(previous)} bulletins in the previous output; {len(targets)} have fewer than {a.min_relations} relations; "
          f"{len(missing)} NER bulletins are not in it ({'will be run' if a.include_missing else 'skipped: use --include-missing'})")
    bulletins = {b.bulletin_id: b for b in load_bulletins(a.input, ALL_ENTITY_TYPES, a.min_ner_confidence, set(target_ids))}
    prev_by_id = {r["bulletin_id"]: r for r in previous}

    if a.dry_run:
        total: Counter = Counter()
        for bid in target_ids:
            plan = plan_refinement(bulletins[bid], prev_by_id.get(bid), cfg)
            total.update(new_pairs=plan["new_pairs"], skipped=plan["skipped"], requests=plan["requests"], approx_chars=plan["approx_chars"], bulletins=1)
            note = " (previous output has no `pairs`: full re-run)" if plan["replaced"] else ""
            print(f"  {bid}: {plan['new_pairs']} new pairs ({plan['skipped']} already decided), {plan['requests']} requests, ~{plan['approx_chars']:,} characters{note}")
        print(f"dry run: {dict(total)}")
        return 0

    out = Path(a.out)
    if a.restart and out.exists():
        out.unlink()
    done = _done_ids(out)
    if done:
        print(f"{len(done)} bulletins are already in {out}: continuing")
    out.parent.mkdir(parents=True, exist_ok=True)
    client = client or make_client()
    report: list[dict[str, Any]] = []
    totals: Counter = Counter()
    still_low: list[str] = []
    todo = set(target_ids)
    with open(out, "a", encoding="utf-8") as fh:
        for rec in previous:
            bid = rec["bulletin_id"]
            if bid in done:
                continue
            if bid in todo:
                new, info = refine_bulletin(bulletins[bid], rec, client, cfg, choice_factory, a.min_relations)
                totals.update(refined=1, new_pairs=info["new_pairs"], skipped=info["skipped"], requests=info["requests"], new_relations=info["new_relations"])
                report.append(dict(bulletin_id=bid, relations_before=count_relations(rec), relations_after=count_relations(new), **info))
                print(f"{bid}: {info['new_pairs']} new pairs ({info['skipped']} already decided), {info['requests']} requests, relations {count_relations(rec)} -> {count_relations(new)}")
                rec = new
            if needs_refinement(rec, a.min_relations):
                still_low.append(bid)
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
        for bid in (i for i in target_ids if i not in in_previous and i not in done):         # bulletins that were not in the previous output
            new, info = refine_bulletin(bulletins[bid], None, client, cfg, choice_factory, a.min_relations)
            totals.update(refined=1, new_pairs=info["new_pairs"], requests=info["requests"], new_relations=info["new_relations"])
            report.append(dict(bulletin_id=bid, relations_before=None, relations_after=count_relations(new), **info))
            print(f"{bid}: new bulletin, {info['new_pairs']} pairs, {info['requests']} requests, {count_relations(new)} relations")
            if needs_refinement(new, a.min_relations):
                still_low.append(bid)
            fh.write(json.dumps(new, ensure_ascii=False) + "\n")
            fh.flush()
    print(f"done: {dict(totals)}; {len(still_low)} bulletins still have fewer than {a.min_relations} relations -> {out}")
    if a.report:
        Path(a.report).write_text(json.dumps(dict(totals=dict(totals), still_below_threshold=still_low, bulletins=report), indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
