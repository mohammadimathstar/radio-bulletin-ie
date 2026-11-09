import html

from collections import defaultdict

from typesafe_sdk import Choice

from .models.models import ContextGroup, JEVBatch
from .models.schema_old import RELATION_SCHEMA, NO_RELATION


# ---------------------------------------------------------
# JEV instructions
# ---------------------------------------------------------

JEV_INSTRUCTIONS = """
You are a relation classification system for historical
Dutch radio bulletins from 1939.

Your task is to classify the relationship between two
specified entity mentions in a bulletin.

INPUT

The shared state contains:
- Contexts containing original Dutch text.
- Entity mentions marked with <e> tags.
- Mention IDs and entity types.
- Target entity pairs.

Each question specifies one target pair and its context.

IMPORTANT RULES

1. Only classify the target pair specified in the question.

2. Entity IDs identify individual mentions, not necessarily
   unique real-world entities.

3. Entity types are provided by the NER system.
   Do not reclassify entities.

4. The text inside entity markers is the original mention text.
   Do not modify entity names.

5. Only select one of the provided options.

6. A relation must be supported by the supplied text.
   Do not use external historical knowledge to infer relations.

7. The order of entity mentions in the text does not determine
   the semantic direction of a relation.

8. For directional relations, select the option indicating
   the correct semantic head and tail.

9. For symmetric relations, select the symmetric option.

10. If no candidate relation is supported by the text,
    select no_relation.

11. Do not infer relations merely because two entities occur
    close to each other.

12. Consider the historical context of the Dutch bulletin,
    but do not introduce facts that are not supported by
    the provided text.

13. If the text is ambiguous or insufficient to establish
    a relation, select no_relation.

Return exactly one classification for this question.
"""


# ---------------------------------------------------------
# Entity marker rendering
# ---------------------------------------------------------

def render_marked_context(
    text: str,
    mentions,
    start: int,
    end: int,
) -> str:
    """
    Render a text context with entity markers.

    The surrounding context remains ordinary text.

    Example:

        The <e id="M1" type="Person">Chamberlain</e>
        met with <e id="M2" type="Person">Ribbentrop</e>.

    Original text is HTML/XML escaped where necessary.
    This prevents OCR characters such as '<' and '&' from
    accidentally breaking the marker structure.
    """

    relevant = [
        mention
        for mention in mentions
        if mention.start >= start
        and mention.end <= end
    ]

    relevant.sort(
        key=lambda mention: (
            mention.start,
            mention.end,
        )
    )

    parts = []
    cursor = start

    for mention in relevant:

        if mention.start < cursor:
            raise ValueError(
                "Overlapping entity mentions cannot be represented "
                f"with simple markers: {mention.mention_id}"
            )

        # Preserve the surrounding text.
        parts.append(
            html.escape(text[cursor:mention.start], quote=False)
        )

        # Mark the entity mention.
        mention_id = html.escape(
            mention.mention_id,
            quote=True,
        )

        entity_type = html.escape(
            mention.entity_type,
            quote=True,
        )

        mention_text = html.escape(
            text[mention.start:mention.end],
            quote=False,
        )

        parts.append(
            f'<e id="{mention_id}" type="{entity_type}">'
            f'{mention_text}'
            f'</e>'
        )

        cursor = mention.end

    parts.append(
        html.escape(text[cursor:end], quote=False)
    )

    return "".join(parts)


# ---------------------------------------------------------
# Build classification options
# ---------------------------------------------------------

def build_relation_options(
    entity1,
    entity2,
    candidate_relations: list[str],
):
    """
    Build Choice options for a candidate pair.

    Each directional relation can have two options:

        relation__entity1_to_entity2
        relation__entity2_to_entity1

    Symmetric relations have one option:

        interacts_with

    Returns:
        criteria: TypeSafe Choice criteria.
        option_map: Mapping from option key to semantic output.
    """

    criteria = {}
    option_map = {}

    type1 = entity1.entity_type
    type2 = entity2.entity_type

    for relation in candidate_relations:

        definition = RELATION_SCHEMA[relation]

        if definition.symmetric:

            option_key = relation

            criteria[option_key] = (
                definition.description
                + " This relationship is symmetric; "
                  "the order of the two entities does not matter."
            )

            option_map[option_key] = {
                "relation": relation,
                "head": entity1.mention_id,
                "tail": entity2.mention_id,
            }

            continue

        allowed = definition.allowed_types

        # Direction: entity1 -> entity2.
        if (type1, type2) in allowed:

            option_key = f"{relation}__entity1_to_entity2"

            criteria[option_key] = (
                definition.description
                + f" Semantic direction: "
                  f"{entity1.mention_id} is the head and "
                  f"{entity2.mention_id} is the tail."
            )

            option_map[option_key] = {
                "relation": relation,
                "head": entity1.mention_id,
                "tail": entity2.mention_id,
            }

        # Direction: entity2 -> entity1.
        if (type2, type1) in allowed:

            option_key = f"{relation}__entity2_to_entity1"

            criteria[option_key] = (
                definition.description
                + f" Semantic direction: "
                  f"{entity2.mention_id} is the head and "
                  f"{entity1.mention_id} is the tail."
            )

            option_map[option_key] = {
                "relation": relation,
                "head": entity2.mention_id,
                "tail": entity1.mention_id,
            }

    # Explicit negative option.
    criteria[NO_RELATION] = (
        "The text does not establish any of the listed "
        "relationships between these two mentions."
    )

    option_map[NO_RELATION] = {
        "relation": NO_RELATION,
        "head": None,
        "tail": None,
    }

    return criteria, option_map


# ---------------------------------------------------------
# Batch preparation
# ---------------------------------------------------------

def build_jev_batches(
    text: str,
    mentions,
    context_groups: list[ContextGroup],
    max_questions_per_request: int = 20,
    bulletin_id: str | None = None,
    bulletin_date: str | None = None,
) -> list[JEVBatch]:
    """
    Prepare multiple Choice questions for each TypeSafe request.

    Every candidate pair becomes one Choice question.

    All questions in a request share the same state, which contains
    the relevant marked contexts and target-pair metadata.

    Contexts are included only once per batch.

    max_questions_per_request controls the maximum number of
    candidate pairs classified in one system_one call.
    """

    if max_questions_per_request < 1:
        raise ValueError(
            "max_questions_per_request must be at least 1"
        )

    # Flatten pairs while retaining their context groups.
    flattened = []

    for group in context_groups:
        for pair in group.pairs:
            flattened.append((group, pair))

    batches = []

    for batch_index, offset in enumerate(
        range(0, len(flattened), max_questions_per_request),
        start=1,
    ):

        chunk = flattened[
            offset:offset + max_questions_per_request
        ]

        contexts = {}

        questions = {}
        option_maps = {}
        pair_metadata = {}

        for group, pair in chunk:

            # Add each context only once in this batch.
            if group.context_id not in contexts:

                marked_context = render_marked_context(
                    text,
                    mentions,
                    group.context_start,
                    group.context_end,
                )

                contexts[group.context_id] = {
                    "context": marked_context,
                    "target_pairs": [],
                }

            context = contexts[group.context_id]

            # Add target pair information to the shared state.
            context["target_pairs"].append({
                "pair_id": pair.pair_id,
                "entity1": {
                    "mention_id": pair.entity1.mention_id,
                    "type": pair.entity1.entity_type,
                },
                "entity2": {
                    "mention_id": pair.entity2.mention_id,
                    "type": pair.entity2.entity_type,
                },
            })

            # Build classification options.
            criteria, option_map = build_relation_options(
                pair.entity1,
                pair.entity2,
                pair.candidate_relations,
            )

            question_id = f"q_{pair.pair_id}"

            instructions = (
                f"{JEV_INSTRUCTIONS}\n\n"
                f"CLASSIFICATION TASK:\n"
                f"Use context {group.context_id}.\n"
                f"Classify pair {pair.pair_id}.\n"
                f"Entity 1: {pair.entity1.mention_id} "
                f"(type: {pair.entity1.entity_type}).\n"
                f"Entity 2: {pair.entity2.mention_id} "
                f"(type: {pair.entity2.entity_type}).\n"
                f"Select exactly one option from the criteria."
            )

            questions[question_id] = Choice(
                instructions=instructions,
                criteria=criteria,
            )

            option_maps[question_id] = option_map

            pair_metadata[question_id] = {
                "pair_id": pair.pair_id,
                "context_id": group.context_id,
                "entity1": pair.entity1.mention_id,
                "entity2": pair.entity2.mention_id,
            }

        # Shared state for all Choice questions.
        state = {
            "bulletin_id": bulletin_id,
            "bulletin_date": bulletin_date,
            "contexts": [
                {
                    "context_id": context_id,
                    **context_data,
                }
                for context_id, context_data in contexts.items()
            ],
        }

        batches.append(
            JEVBatch(
                state=state,
                questions=questions,
                option_maps=option_maps,
                pair_metadata=pair_metadata,
            )
        )

    return batches


# ---------------------------------------------------------
# Execute JEV
# ---------------------------------------------------------

def classify_batch(
    client,
    batch: JEVBatch,
    model: str = "jev-latest",
) -> list[dict]:
    """
    Execute all Choice questions in one TypeSafe system_one call.

    Returns one classification per candidate pair, including
    no_relation predictions.

    The response includes:
        - pair_id
        - relation
        - head mention ID
        - tail mention ID
        - selected-option confidence
        - complete option probability distribution
    """

    response = client.system_one(
        state=batch.state,
        questions=batch.questions,
        model=model,
    )

    results = []

    for question_id, option_map in batch.option_maps.items():

        answer = response.answers[question_id]

        selected_option = answer.choice

        if selected_option not in option_map:
            raise ValueError(
                f"Unexpected JEV option: {selected_option}"
            )

        prediction = option_map[selected_option]

        metadata = batch.pair_metadata[question_id]

        probabilities = {
            str(key): float(value)
            for key, value in dict(
                answer.probabilities
            ).items()
        }

        results.append({
            "pair_id": metadata["pair_id"],
            "context_id": metadata["context_id"],

            "entity1": metadata["entity1"],
            "entity2": metadata["entity2"],

            "relation": prediction["relation"],

            "head_mention_id": prediction["head"],
            "tail_mention_id": prediction["tail"],

            "selected_option": selected_option,
            "confidence": float(answer.confidence),
            "probabilities": probabilities,
        })

    return results


def classify_all(
    client,
    batches: list[JEVBatch],
    model: str = "jev-latest",
) -> list[dict]:
    """
    Execute all prepared batches sequentially.

    Every batch results in one system_one request.
    """

    all_results = []

    for batch_number, batch in enumerate(batches, start=1):

        print(
            f"Processing batch {batch_number}/{len(batches)} "
            f"({len(batch.questions)} questions)"
        )

        results = classify_batch(
            client=client,
            batch=batch,
            model=model,
        )

        all_results.extend(results)

    return all_results


# ---------------------------------------------------------
# Knowledge graph output
# ---------------------------------------------------------

def get_relations_only(
    predictions: list[dict],
) -> list[dict]:
    """
    Remove no_relation predictions.

    Returns only positive relation predictions.
    """

    return [
        prediction
        for prediction in predictions
        if prediction["relation"] != NO_RELATION
    ]