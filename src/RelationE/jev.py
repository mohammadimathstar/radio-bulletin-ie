"""
JEV: marked contexts, answer options, batches, and the calls.

STATE. One request holds several questions that share ONE state: the contexts (original text with every mention marked) and, by default, the general instructions
(shared_instructions=True). Marker format: <e id="e12" type="Person">...</e id="e12">. Closing tags carry the id because mentions can be NESTED (an event phrase that contains two clubs)
or even cross; the earlier renderer raised an error for that and for duplicate spans.
OPTIONS. For every pair: one option per relation and direction that the entity TYPES allow ("beat__entity1_to_entity2"), one option per symmetric relation, and exactly ONE no_relation option.
QUESTIONS. Per question only a short task line (pair id, context id, entities); with shared_instructions=False the full instructions are repeated in every question as before
(about 20 x 1.7k characters more per request).
The typesafe_sdk is imported only when needed (a Choice factory can be injected), so everything else runs and is tested without it.
"""
from __future__ import annotations

import html
import time
from typing import Any, Callable

from .models import Bulletin, CandidatePair, ContextGroup, JEVBatch, Mention, PairPrediction
from .schema import NO_RELATION, RelationDefinition, get_schema

JEV_INSTRUCTIONS = """You are a relation classification system for historical Dutch radio bulletins from 1939.

Classify the relationship between two specified entity mentions in a bulletin.

INPUT
The shared state contains contexts with original Dutch text (OCR: old spelling, errors). Entity mentions are marked <e id="..." type="...">text</e id="...">; the closing tag repeats
the id because mentions can be nested, e.g. a match phrase containing two clubs. Each question names one target pair and one context.

RULES
1. Classify only the target pair of the question.
2. Mention ids identify occurrences, not necessarily different real-world entities. Types come from the NER system: do not reclassify.
3. Select exactly one of the provided options. A relation must be supported by the supplied text; do not use outside historical knowledge.
4. The order in the text does not decide the direction. For a directional relation choose the option with the correct head (subject) and tail (object); for a symmetric relation choose the symmetric option.
5. Being close to each other in the text is not a relation. If no listed relation is established by the text, or the text is ambiguous or insufficient, choose no_relation.
6. A mention that sits inside another mention's phrase (a club inside a match phrase) can still be related to it (it takes part in it)."""

GLOSSARY_RULE = ("\n7. If the state has a relation_glossary, it gives the full definition and Dutch cue phrases of every relation named in the options; "
                 "an option shows only a short gloss and the head/tail mention ids.")

ChoiceFactory = Callable[..., Any]


def default_choice_factory() -> ChoiceFactory:
    from typesafe_sdk import Choice
    return Choice


def render_marked_context(text: str, 
                          mentions: list[Mention], 
                          start: int, end: int) -> str:
    """text[start:end] with every mention that lies completely inside written as <e id=".." type="..">..</e id="..">. Nested, duplicate and crossing mentions are fine.
    The text is HTML-escaped so OCR characters such as '<' or '&' cannot break the markers."""
    inside = [m for m in mentions if m.start >= start and m.end <= end and m.end > m.start]
    events: list[tuple[int, int, int, str, Mention]] = []
    for m in inside:
        events.append((m.start, 1, -m.end, m.mention_id, m))          # opens: at one position the longest (outermost) first
        events.append((m.end, 0, -m.start, m.mention_id, m))          # closes: before opens at the same position; innermost (latest start) first
    events.sort(key=lambda e: (e[0], e[1], e[2], e[3]))
    parts, cursor = [], start
    for pos, kind, _, _, m in events:
        parts.append(html.escape(text[cursor:pos], quote=False))
        mid, mtype = html.escape(m.mention_id, quote=True), html.escape(m.entity_type, quote=True)
        parts.append(f'<e id="{mid}" type="{mtype}">' if kind == 1 else f'</e id="{mid}">')
        cursor = pos
    parts.append(html.escape(text[cursor:end], quote=False))
    return "".join(parts)


def short_description(description: str) -> str:
    """The definition without the list of Dutch cue phrases ('Look for ...')."""
    return description.split(" Look for")[0].split(" Not for")[0].strip()
 


def build_relation_options(entity1: Mention, 
                           entity2: Mention, 
                           candidate_relations: list[str], 
                           schema: dict[str, RelationDefinition] | None = None,
                           compact: bool = False) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    """(criteria for the Choice question, option -> {relation, head, tail}). no_relation is added exactly once and is never a candidate relation.
    compact=True: a short gloss and the head/tail ids instead of the full definition (which then belongs in the state's relation_glossary)."""
    schema = schema or get_schema("fine")
    criteria: dict[str, str] = {}
    option_map: dict[str, dict[str, Any]] = {}
    t1, t2 = entity1.entity_type, entity2.entity_type
    for rel in candidate_relations:
        if rel == NO_RELATION:
            continue
        d = schema[rel]
        if d.symmetric:
            criteria[rel] = (short_description(d.description) + " (symmetric: the order does not matter)") if compact else \
                d.description + " This relationship is symmetric: the order of the two mentions does not matter."
            option_map[rel] = {"relation": rel, "head": entity1.mention_id, "tail": entity2.mention_id}
            # criteria[rel] = d.description + " This relationship is symmetric: the order of the two mentions does not matter."
            # option_map[rel] = {"relation": rel, "head": entity1.mention_id, "tail": entity2.mention_id}
            continue
        for suffix, head, tail, ok in (("entity1_to_entity2", entity1, entity2, (t1, t2) in d.allowed_types),
                                       ("entity2_to_entity1", entity2, entity1, (t2, t1) in d.allowed_types)):
            if ok:
                key = f"{rel}__{suffix}"
                criteria[key] = (short_description(d.description) + f" [head={head.mention_id}, tail={tail.mention_id}]") if compact else \
                    d.description + f" Semantic direction: {head.mention_id} is the head (subject) and {tail.mention_id} is the tail (object)."
                # criteria[key] = d.description + f" Semantic direction: {head.mention_id} is the head (subject) and {tail.mention_id} is the tail (object)."
                option_map[key] = {"relation": rel, "head": head.mention_id, "tail": tail.mention_id}
    criteria[NO_RELATION] = "The text does not establish any of the listed relationships between these two mentions."
    option_map[NO_RELATION] = {"relation": NO_RELATION, "head": None, "tail": None}
    return criteria, option_map


def build_jev_batches(
        bulletin: Bulletin, 
        context_groups: list[ContextGroup], 
        schema: dict[str, RelationDefinition] | None = None, 
        max_questions_per_request: int = 20,
        choice_factory: ChoiceFactory | None = None, 
        shared_instructions: bool = True,
        compact_options: bool = False
    ) -> list[JEVBatch]:
    """Questions for all pairs, in batches. The pairs of one context stay together; each context appears once per batch."""
    if max_questions_per_request < 1:
        raise ValueError("max_questions_per_request must be at least 1")
    schema = schema or get_schema("fine")
    choice = choice_factory or default_choice_factory()
    flat = [(g, p) for g in context_groups for p in g.pairs]
    batches = []
    for offset in range(0, len(flat), max_questions_per_request):
        contexts: dict[str, dict[str, Any]] = {}
        questions: dict[str, Any] = {}
        option_maps: dict[str, dict[str, dict[str, Any]]] = {}
        meta: dict[str, dict[str, Any]] = {}
        for g, p in flat[offset:offset + max_questions_per_request]:
            ctx = contexts.setdefault(g.context_id, {"context_id": g.context_id, "context": render_marked_context(bulletin.text, bulletin.mentions, g.context_start, g.context_end),
                                                    "target_pairs": []})
            ctx["target_pairs"].append({"pair_id": p.pair_id, "entity1": {"mention_id": p.entity1.mention_id, "type": p.entity1.entity_type},
                                        "entity2": {"mention_id": p.entity2.mention_id, "type": p.entity2.entity_type}})
            criteria, option_map = build_relation_options(p.entity1, p.entity2, p.candidate_relations, schema, compact_options)
            qid = f"q_{p.pair_id}"
            task = (f"CLASSIFICATION TASK: use context {g.context_id}. Classify pair {p.pair_id}: entity 1 = {p.entity1.mention_id} (type: {p.entity1.entity_type}), "
                    f"entity 2 = {p.entity2.mention_id} (type: {p.entity2.entity_type}). Select exactly one option.")
            # questions[qid] = choice(instructions=task if shared_instructions else f"{JEV_INSTRUCTIONS}\n\n{task}", criteria=criteria)
            questions[qid] = choice(instructions=task if shared_instructions else f"{JEV_INSTRUCTIONS}{GLOSSARY_RULE if compact_options else ''}\n\n{task}", criteria=criteria)
            option_maps[qid] = option_map
            meta[qid] = {"pair_id": p.pair_id, "context_id": g.context_id, "entity1": p.entity1.mention_id, "entity2": p.entity2.mention_id}
        state: dict[str, Any] = {"bulletin_id": bulletin.bulletin_id, "bulletin_date": bulletin.date, "contexts": list(contexts.values())}
        if shared_instructions:
            state["instructions"] = JEV_INSTRUCTIONS + (GLOSSARY_RULE if compact_options else "")
        if compact_options:                                       # the full definitions once per request instead of once per option
            used = sorted({info["relation"] for om in option_maps.values() for info in om.values() if info["relation"] != NO_RELATION})
            state["relation_glossary"] = {r: schema[r].description for r in used}
            # state["instructions"] = JEV_INSTRUCTIONS
        batches.append(JEVBatch(state, questions, option_maps, meta))
    return batches


def classify_batch(
        client: Any, 
        batch: JEVBatch, 
        model: str = "jev-latest", 
        retries: int = 2, 
        backoff: float = 2.0
    ) -> list[PairPrediction]:
    """One system_one call for the whole batch; a failing call is repeated (retries) before the error is raised."""
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = client.system_one(state=batch.state, questions=batch.questions, model=model)
            break
        except Exception as ex:                                  # network, rate limit, server error
            last = ex
            if attempt == retries:
                raise RuntimeError(f"JEV request failed after {retries + 1} attempts: {ex!r}") from last
            time.sleep(backoff * (2 ** attempt) if backoff else 0)
    out = []
    for qid, option_map in batch.option_maps.items():
        answer = response.answers[qid]
        if answer.choice not in option_map:
            raise ValueError(f"Unexpected JEV option for {qid}: {answer.choice}")
        m = batch.pair_metadata[qid]
        out.append(PairPrediction(m["pair_id"], m["context_id"], m["entity1"], m["entity2"], answer.choice, float(answer.confidence),
                                  {str(k): float(v) for k, v in dict(answer.probabilities).items()}, option_map))
    return out


def classify_all(
        client: Any, 
        batches: list[JEVBatch], 
        model: str = "jev-latest", 
        retries: int = 2, 
        backoff: float = 2.0, 
        progress: bool = False
    ) -> list[PairPrediction]:
    results: list[PairPrediction] = []
    for n, b in enumerate(batches, 1):
        if progress:
            print(f"  batch {n}/{len(batches)} ({len(b.questions)} questions)")
        results += classify_batch(client, b, model, retries, backoff)
    return results


def make_client() -> Any:
    """The real JEV client (pip install typesafe-sdk; TYPESAFE_API_KEY in the environment)."""
    from typesafe_sdk import TypeSafeClient
    return TypeSafeClient()
