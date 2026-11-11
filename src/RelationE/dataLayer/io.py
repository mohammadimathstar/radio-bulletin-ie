"""
Reading the NER output (JSONL, one bulletin per line) and cleaning it for relation extraction.

Expected fields per line: bulletin_id, bulletin_date, text, entities [{id, text, normalized_name, start, end, annotation_confidence, type, ...}]. Only the TYPE of an entity is used
(subtype, topics, event fields are ignored). Cleaning, with counts in bulletin.load_stats:
    unknown_type        the type is not in the schema: the mention is dropped (its pairs could not be classified)
    low_confidence      annotation_confidence below min_confidence (default: keep everything)
    repaired_offsets    text[start:end] was not the mention text, but the text occurs close by: the offsets were corrected
    bad_offsets         the mention text cannot be found at or near its offsets: dropped
    duplicate_span      the same (start, end, type) listed twice (e.g. e11/e13 in the sample): one kept, the more confident
    type_conflict       the same span with two different types: the more confident one is kept
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Iterator

from .models import Bulletin, Mention
from .schema import ALL_ENTITY_TYPES


def parse_bulletin(record: dict[str, Any], allowed_types: Iterable[str] = ALL_ENTITY_TYPES, min_confidence: float = 0.0) -> Bulletin:
    text, allowed, stats = record["text"], set(allowed_types), Counter()
    kept: dict[tuple[int, int], Mention] = {}
    for e in record.get("entities", []):
        if e.get("type") not in allowed:
            stats["unknown_type"] += 1
            continue
        conf = e.get("annotation_confidence")
        if conf is not None and conf < min_confidence:
            stats["low_confidence"] += 1
            continue
        start, end, surface = e["start"], e["end"], e["text"]
        if not (0 <= start < end <= len(text)) or text[start:end] != surface:
            pos = text.find(surface, max(0, start - 60), min(len(text), end + 60 + len(surface))) if surface else -1
            if pos < 0:
                stats["bad_offsets"] += 1
                continue
            start, end = pos, pos + len(surface)
            stats["repaired_offsets"] += 1
        m = Mention(str(e["id"]), surface, e["type"], start, end, e.get("normalized_name"), conf)
        old = kept.get((start, end))
        if old is None:
            kept[(start, end)] = m
            continue
        stats["duplicate_span" if old.entity_type == m.entity_type else "type_conflict"] += 1
        if (m.confidence or 0) > (old.confidence or 0):
            kept[(start, end)] = m
    mentions = sorted(kept.values(), key=lambda m: (m.start, m.end))
    return Bulletin(record["bulletin_id"], record.get("bulletin_date"), text, mentions, dict(stats))


def load_bulletins(path: str | Path, 
                   allowed_types: Iterable[str] = ALL_ENTITY_TYPES, 
                   min_confidence: float = 0.0, 
                   ids: set[str] | None = None,
                   limit: int | None = None) -> Iterator[Bulletin]:
    n = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            if ids is not None and rec["bulletin_id"] not in ids:
                continue
            yield parse_bulletin(rec, allowed_types, min_confidence)
            n += 1
            if limit and n >= limit:
                return


def done_ids(path: str | Path) -> set[str]:
    p = Path(path)
    if not p.exists():
        return set()
    with open(p, encoding="utf-8") as fh:
        return {json.loads(l)["bulletin_id"] for l in fh if l.strip()}


def type_counts(path: str | Path) -> Counter:
    """Entity types in a NER file (for schema checks)."""
    c: Counter = Counter()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                c.update(e.get("type") for e in json.loads(line).get("entities", []))
    return c
