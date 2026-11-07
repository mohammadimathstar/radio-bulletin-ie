import json

import spacy

from dotenv import load_dotenv
from typesafe_sdk import TypeSafeClient

from .models import Mention

from .candidate_generation import (
    CandidateConfig,
    assign_sentence_ids,
    generate_candidates,
    group_candidates,
)

from .jev import (
    build_jev_batches,
    classify_all,
    get_relations_only,
)


def main():

    load_dotenv()

    # -------------------------------------------------
    # 1. Load spaCy
    # -------------------------------------------------

    nlp = spacy.load("nl_core_news_lg")

    # -------------------------------------------------
    # 2. Original bulletin text
    # -------------------------------------------------

    text = """
    De Britsche minister-president Neville Chamberlain
    heeft een onderhoud gehad met den Duitschen gezant
    te Berlijn.
    """

    # -------------------------------------------------
    # 3. Example NER output
    # -------------------------------------------------

    mentions = [
        Mention(
            mention_id="M1",
            text="Neville Chamberlain",
            entity_type="Person",
            start=text.index("Neville Chamberlain"),
            end=text.index("Neville Chamberlain")
                + len("Neville Chamberlain"),
        ),

        Mention(
            mention_id="M2",
            text="Duitschen gezant",
            entity_type="Person",
            start=text.index("Duitschen gezant"),
            end=text.index("Duitschen gezant")
                + len("Duitschen gezant"),
        ),

        Mention(
            mention_id="M3",
            text="Berlijn",
            entity_type="Place",
            start=text.index("Berlijn"),
            end=text.index("Berlijn") + len("Berlijn"),
        ),
    ]

    # -------------------------------------------------
    # 4. Sentence segmentation after NER
    # -------------------------------------------------

    sentence_spans = assign_sentence_ids(
        text=text,
        mentions=mentions,
        nlp=nlp,
    )

    # -------------------------------------------------
    # 5. Candidate generation configuration
    # -------------------------------------------------

    config = CandidateConfig(
        max_sentence_distance=1,
        max_character_distance=200,
        similarity_threshold=0.85,
        context_padding=80,
    )

    # -------------------------------------------------
    # 6. Generate candidates
    # -------------------------------------------------

    candidates = generate_candidates(
        text=text,
        mentions=mentions,
        sentence_spans=sentence_spans,
        config=config,
    )

    print(f"Generated {len(candidates)} candidates")

    # -------------------------------------------------
    # 7. Group candidates by context
    # -------------------------------------------------

    context_groups = group_candidates(candidates)

    # -------------------------------------------------
    # 8. Prepare JEV batches
    # -------------------------------------------------

    batches = build_jev_batches(
        text=text,
        mentions=mentions,
        context_groups=context_groups,
        max_questions_per_request=20,
        bulletin_id="bulletin_001",
        bulletin_date="1939-09-01",
    )

    print(f"Created {len(batches)} JEV batches")

    # -------------------------------------------------
    # 9. Execute JEV
    # -------------------------------------------------

    with TypeSafeClient() as client:

        predictions = classify_all(
            client=client,
            batches=batches,
            model="jev-latest",
        )

    # -------------------------------------------------
    # 10. Keep positive relationships
    # -------------------------------------------------

    relations = get_relations_only(predictions)

    # -------------------------------------------------
    # 11. Save results
    # -------------------------------------------------

    with open(
        "relations.jsonl",
        "w",
        encoding="utf-8",
    ) as f:

        for relation in relations:

            f.write(
                json.dumps(
                    relation,
                    ensure_ascii=False,
                ) + "\n"
            )

    print(f"Extracted {len(relations)} relations")


if __name__ == "__main__":
    main()