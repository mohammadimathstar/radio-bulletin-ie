"""
export.py - combine the NER result with the relation result, and write Label Studio tasks to check them.

    python -m relation_extraction.export --ner data/entity_annotations_raw.jsonl --relations data/relations_refined.jsonl \
        --combined-out data/ner_re.jsonl --ls-out data/label_studio_tasks.json --ls-config data/label_studio_config.xml

COMBINED RECORD (one JSON line per bulletin): everything of the NER record (text, topics, language, all entities with subtype, normalized_name, confidence, ...) plus
    entities[].status     "kept" if the entity took part in the relation extraction, otherwise why not: unknown_type, low_confidence, bad_offsets, or duplicate_of:<id> (the same span listed twice)
    relations             [{id, relation, coarse, category, head, tail (NER entity ids), head_text, tail_text, head_type, tail_type, probability, p_no_relation, margin,
                            direction_confidence, pair_id, evidence {start, end}}]
    re                    {schema_level, n_pairs, n_requests, n_relations, refinement: [...]}
LABEL STUDIO. One task per bulletin: data = {text, bulletin_id, bulletin_date, topics, review_notes}; the entities (status "kept") are labelled regions, the relations are Label Studio
relations from the head to the tail region (direction "right"), all as PREDICTIONS (pre-annotations: the reviewer accepts or corrects them; --as annotations makes them editable
annotations at once). Entities are labelled with their type (Person, Organization, Place, Event, Vehicle) or, with --entity-labels subtype, with their subtype. Nested and overlapping
entities are fine in Label Studio. The labeling config (--ls-config) lists the labels and every relation type: paste it into the project (Settings > Labeling Interface > Code) BEFORE
importing the tasks; the names (from_name "label", to_name "text") must match it.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .dataLayer.io import parse_bulletin
from .dataLayer.schema import ALL_ENTITY_TYPES, FINE_RELATIONS, get_schema

_COLORS = {"Person": "#e8590c", "Organization": "#1c7ed6", "Place": "#2f9e44", "Event": "#ae3ec9", "Vehicle": "#f59f00", "LegalDocument": "#868e96"}


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


# ------------------------------------------------------------------ combining
def entity_statuses(ner: dict[str, Any], allowed_types=ALL_ENTITY_TYPES, min_confidence: float = 0.0) -> dict[str, str]:
    """For every NER entity id: 'kept', or the reason it did not take part in the relation extraction (see the module docstring)."""
    kept = {m.mention_id: (m.start, m.end) for m in parse_bulletin(ner, allowed_types, min_confidence).mentions}
    by_span = {span: mid for mid, span in kept.items()}
    text, out = ner["text"], {}
    for e in ner["entities"]:
        eid = str(e["id"])
        if eid in kept:
            out[eid] = "kept"
        elif e.get("type") not in set(allowed_types):
            out[eid] = "unknown_type"
        elif (e.get("annotation_confidence") or 1.0) < min_confidence:
            out[eid] = "low_confidence"
        else:
            start = e["start"] if text[e["start"]:e["end"]] == e["text"] else text.find(e["text"], max(0, e["start"] - 60), e["end"] + 60 + len(e["text"]))
            span = (start, start + len(e["text"])) if start >= 0 else None
            out[eid] = f"duplicate_of:{by_span[span]}" if span in by_span else "bad_offsets"
    return out


def combine(ner: dict[str, Any], re_rec: dict[str, Any], allowed_types=ALL_ENTITY_TYPES, min_probability: float = 0.0, min_ner_confidence: float = 0.0) -> dict[str, Any]:
    """The NER record with the relations of the RE record added (relations below min_probability are left out)."""
    status = entity_statuses(ner, allowed_types, min_ner_confidence)
    rels = []
    for r in sorted((r for r in re_rec["relations"] if r["probability"] >= min_probability), key=lambda r: (r["head"]["start"], r["tail"]["start"], r["relation"])):
        rels.append(dict(id=f"r{len(rels) + 1}", relation=r["relation"], coarse=r.get("coarse"), category=r.get("category"), head=r["head"]["mention_id"], tail=r["tail"]["mention_id"],
                         head_text=r["head"]["text"], tail_text=r["tail"]["text"], head_type=r["head"]["type"], tail_type=r["tail"]["type"], probability=r["probability"],
                         p_no_relation=r["p_no_relation"], margin=r["margin"], direction_confidence=r["direction_confidence"], pair_id=r["pair_id"],
                         evidence=dict(start=r["evidence"]["start"], end=r["evidence"]["end"])))
    combined = {k: v for k, v in ner.items() if k != "entities"}
    combined["entities"] = [dict(e, status=status[str(e["id"])]) for e in ner["entities"]]
    combined["relations"] = rels
    combined["re"] = dict(schema_level=re_rec.get("schema_level"), n_pairs=re_rec.get("n_pairs"), n_requests=re_rec.get("n_requests"), n_relations=len(rels),
                          refinement=re_rec.get("refinement", []))
    return combined


# ------------------------------------------------------------------ Label Studio
def entity_label(e: dict[str, Any], entity_labels: str = "type") -> str:
    return (e.get("subtype") or e["type"]) if entity_labels == "subtype" else e["type"]


def label_studio_task(combined: dict[str, Any], entity_labels: str = "type", as_: str = "predictions") -> dict[str, Any]:
    """One Label Studio task: the text, the entities as labelled regions, the relations between them."""
    text, result = combined["text"], []
    kept = [e for e in combined["entities"] if e["status"] == "kept"]
    ids = {str(e["id"]) for e in kept}
    for e in kept:
        item: dict[str, Any] = {"id": str(e["id"]), "from_name": "label", "to_name": "text", "type": "labels",
                                "value": {"start": e["start"], "end": e["end"], "text": text[e["start"]:e["end"]], "labels": [entity_label(e, entity_labels)]}}
        if e.get("annotation_confidence") is not None:
            item["score"] = e["annotation_confidence"]
        result.append(item)
    for r in combined["relations"]:
        if r["head"] in ids and r["tail"] in ids:
            result.append({"from_id": r["head"], "to_id": r["tail"], "type": "relation", "direction": "right", "labels": [r["relation"]],
                           "meta": {"text": [f"p={r['probability']} margin={r['margin']} direction={r['direction_confidence']} {r['pair_id']}"]}, "score": r["probability"]})
    dropped = [f"{e['id']} {e['text']!r}: {e['status']}" for e in combined["entities"] if e["status"] != "kept"]
    notes = f"{len(combined['relations'])} relations" + (f"; not used: {'; '.join(dropped)}" if dropped else "")
    task: dict[str, Any] = {"data": {"text": text, "bulletin_id": combined["bulletin_id"], "bulletin_date": combined.get("bulletin_date"),
                                     "topics": ", ".join(combined.get("topics") or []), "review_notes": notes}}
    if as_ == "annotations":
        task["annotations"] = [{"result": result}]
    else:
        task["predictions"] = [{"model_version": "ner+jev", "result": result}]
    return task


def label_studio_config(combined_records: list[dict[str, Any]], entity_labels: str = "type", level: str = "fine") -> str:
    """Labeling config (XML): the entity labels that occur (coloured by type) and every relation type of the schema level plus any other used."""
    label_type: dict[str, str] = {}
    used_relations: set[str] = set()
    for c in combined_records:
        for e in c["entities"]:
            if e["status"] == "kept":
                label_type.setdefault(entity_label(e, entity_labels), e["type"])
        used_relations |= {r["relation"] for r in c["relations"]}
    if entity_labels == "type":
        label_type.update({t: t for t in ALL_ENTITY_TYPES})
    labels = "\n".join(f'    <Label value="{l}" background="{_COLORS.get(t, "#868e96")}"/>' for l, t in sorted(label_type.items(), key=lambda kv: (kv[1], kv[0])))
    relations = "\n".join(f'    <Relation value="{r}"/>' for r in sorted(set(get_schema(level)) | used_relations))
    return ('<View>\n  <Header value="$bulletin_id ($bulletin_date)"/>\n  <Header value="$review_notes"/>\n  <Relations>\n' + relations +
            '\n  </Relations>\n  <Labels name="label" toName="text">\n' + labels + '\n  </Labels>\n  <Text name="text" value="$text"/>\n</View>\n')


# ------------------------------------------------------------------ command line
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="export", description="Combine NER and relations, and export Label Studio tasks")
    p.add_argument("--ner", default="data/entity_annotations_raw.jsonl", help="NER output (JSONL)")
    p.add_argument("--relations", default="data/relations_refined.jsonl", help="relation output (JSONL), e.g. the result of refine.py")
    p.add_argument("--combined-out", default="data/ner_re.jsonl")
    p.add_argument("--ls-out", default="data/label_studio_tasks.json")
    p.add_argument("--ls-config", default="data/label_studio_config.xml")
    p.add_argument("--entity-labels", choices=["type", "subtype"], default="type", help="label the entities with their type or their subtype")
    p.add_argument("--as", dest="as_", choices=["predictions", "annotations"], default="predictions")
    p.add_argument("--min-probability", type=float, default=0.0, help="leave out relations with a lower probability")
    p.add_argument("--min-ner-confidence", type=float, default=0.0, help="the value the relation run used")
    p.add_argument("--include-without-re", action="store_true", help="also bulletins of the NER file that are not in the relation output (without relations)")
    p.add_argument("--only-with-relations", action="store_true", help="only bulletins with at least one relation")
    p.add_argument("--ids", help="a text file with bulletin ids")
    p.add_argument("--limit", type=int)
    a = p.parse_args(argv)

    ner = {r["bulletin_id"]: r for r in read_jsonl(a.ner)}
    re_records = read_jsonl(a.relations)
    wanted = set(Path(a.ids).read_text(encoding="utf-8").split()) if a.ids else None
    combined, missing_ner = [], 0
    for rr in re_records:
        bid = rr["bulletin_id"]
        if wanted is not None and bid not in wanted:
            continue
        if bid not in ner:
            missing_ner += 1
            continue
        combined.append(combine(ner[bid], rr, ALL_ENTITY_TYPES, a.min_probability, a.min_ner_confidence))
    if a.include_without_re:
        have = {c["bulletin_id"] for c in combined}
        for bid, rec in ner.items():
            if bid not in have and (wanted is None or bid in wanted):
                combined.append(combine(rec, dict(relations=[], schema_level=None), ALL_ENTITY_TYPES, a.min_probability, a.min_ner_confidence))
    if a.only_with_relations:
        combined = [c for c in combined if c["relations"]]
    if a.limit:
        combined = combined[: a.limit]
    for path in (a.combined_out, a.ls_out, a.ls_config):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(a.combined_out).write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in combined), encoding="utf-8")
    tasks = [label_studio_task(c, a.entity_labels, a.as_) for c in combined]
    Path(a.ls_out).write_text(json.dumps(tasks, ensure_ascii=False), encoding="utf-8")
    level = next((c["re"]["schema_level"] for c in combined if c["re"]["schema_level"]), "fine")
    Path(a.ls_config).write_text(label_studio_config(combined, a.entity_labels, level), encoding="utf-8")
    rel_counts = Counter(r["relation"] for c in combined for r in c["relations"])
    print(f"{len(combined)} bulletins combined ({sum(len(c['relations']) for c in combined)} relations; {missing_ner} relation records had no NER record) -> {a.combined_out}")
    print(f"Label Studio: {len(tasks)} tasks -> {a.ls_out}; labeling config -> {a.ls_config}; most frequent relations: {dict(rel_counts.most_common(5))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
