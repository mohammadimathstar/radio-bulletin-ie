from openai import OpenAI
import os
from dotenv import load_dotenv
from tqdm import tqdm
import argparse

from src.configs.ner_cfg import ApiConfig
from src.util.io import (
    read_jsonl, load_records_by_id, append_jsonl, 
    existing_ids, log_issue
)
from src.util.correct_llm import correct_llm_offsets
from src.util.splitters import chunk_text

from .models.bulletins import NEROutput, NERExtraction

from .prompts import ENTITY_SYSTEM_PROMPT, build_entity_input
from .validate import validate_entity_types, validate_entity_mentions




LOCATED_STATUSES = ("exact_normalized", "fuzzy", "exact_raw")
SCHEMA_VERSION = "1.0"
ANNOTATION_GUIDELINE_VERSION = "1.0"
LANGUAGE = "nl"

MAX_CHUNK_CHARS = 1000


def call_parse(cfg: ApiConfig, instructions: str, payload: str, response_model: NERExtraction) -> dict:
    """Call the Responses API with Structured Outputs (Pydantic via text_format)."""
    
    response = cfg.client.responses.parse(
        model=cfg.model,
        instructions=instructions,
        input=payload,
        text_format=response_model,
    )
    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError(f"No parsed output. Raw response: {response.output_text}")
    return parsed


def run_ner(
    cfg: ApiConfig, 
    bulletin: dict, 
    bid, 
    issue_output_path: str
) -> dict:
    """Run the NER pipeline with the given configuration and input."""
    
    extraction = call_parse(
        cfg, 
        ENTITY_SYSTEM_PROMPT, 
        build_entity_input(bulletin), 
        NERExtraction)
    ner_dict = extraction.model_dump(mode="json")

    ner_dict["entities"] = validate_entity_types(ner_dict["entities"])

    # Correct entity offsets.
    ner_dict["entities"] = correct_llm_offsets(bulletin["text"], ner_dict["entities"])
        
    # Keep only confidently located entities.
    # located: list[dict] = []
    # dropped: list[dict] = []
    # for e in ner_dict["entities"]:
    #     if e.get("offset_method") in LOCATED_STATUSES:
    #         e.pop("offset_method", None)  # diagnostic, not part of the schema
    #         located.append(e)
    #     else:
    #         dropped.append(e)
    # ner_dict["entities"] = located

    # if dropped:
    #     log_issue(
    #         issue_output_path, bid, "NER",
    #         [f"dropped {len(dropped)} unlocatable entities: "
    #          + ", ".join(e["id"] for e in dropped)],
    #     )

    # Add metadata locally using Python.
    ner_dict.update({
        "bulletin_id": bid,
        "bulletin_date": bulletin.get("bulletin_date"),
        "language": LANGUAGE,
        "schema_version": SCHEMA_VERSION,
        "annotation_guideline_version": ANNOTATION_GUIDELINE_VERSION,
        "text": bulletin["text"],
        'model': cfg.model,
    })

    # Validate the complete output using NEROutput.
    final_output = NEROutput.model_validate(ner_dict)
    
    # Safety net: surviving entities are guaranteed to match, so this should
    # be empty. If it is not, something is genuinely wrong -> raise.
    residual = validate_entity_mentions(bulletin["text"], ner_dict["entities"])
    if residual:
        raise ValueError(f"Residual entity errors for {bid}: {residual}")

    return final_output.model_dump(mode="json")



def run_ner_chunk(
    cfg: ApiConfig,
    bulletin: dict,
    bid,
    issue_output_path: str,
) -> dict:
    """Run chunked NER and merge results at bulletin level."""

    original_text = bulletin["text"]
    chunks = chunk_text(original_text, MAX_CHUNK_CHARS)

    all_entities = []
    all_topics = []

    for chunk_index, (global_offset, chunk) in enumerate(chunks):

        # Use the original bulletin metadata, replacing only its text.
        chunk_bulletin = {
            **bulletin,
            "text": chunk,
        }

        extraction = call_parse(
            cfg,
            ENTITY_SYSTEM_PROMPT,
            build_entity_input(chunk_bulletin),
            NERExtraction,
        )

        chunk_dict = extraction.model_dump(mode="json")

        # Merge topics, preserving order and avoiding duplicates.
        for topic in chunk_dict["topics"]:
            if topic not in all_topics:
                all_topics.append(topic)

        # Validate entity types before correcting offsets.
        entities = validate_entity_types(chunk_dict["entities"])

        # Correct offsets relative to the chunk.
        entities = correct_llm_offsets(chunk, entities)

        # Convert chunk-local offsets to bulletin-global offsets.
        for entity in entities:

            # Check that offsets are available.
            if entity.get("start") is None or entity.get("end") is None:
                print(
                    f"WARNING: Missing offsets in chunk {chunk_index + 1}: "
                    f"{entity.get('id')} - {entity.get('text')!r}"
                )
                continue


            # Correct global offsets.
            entity["start"] += global_offset
            entity["end"] += global_offset

            # Assign a unique ID before adding the entity.
            entity["id"] = f"e{len(all_entities) + 1}"

            # Namespace event IDs by chunk.
            if entity.get("type") == "Event" and entity.get("event_id"):
                entity["event_id"] = (
                    f"chunk_{chunk_index + 1}_{entity['event_id']}"
                )

            all_entities.append(entity)

    # Keep only entities whose offsets were successfully located.
    # located = []
    # dropped = []

    # for entity in all_entities:
    #     if entity.get("offset_method") in LOCATED_STATUSES:
    #         located.append(entity)
    #     else:
    #         dropped.append(entity)

    # if dropped:
    #     log_issue(
    #         issue_output_path,
    #         bid,
    #         "NER",
    #         [
    #             f"dropped {len(dropped)} unlocatable entities: "
    #             + ", ".join(e["id"] for e in dropped)
    #         ],
    #     )

    # # Remove internal offset diagnostics before final validation.
    # for entity in located:
    #     entity.pop("offset_method", None)
    #     entity.pop("offset_score", None)

    ner_dict = {
        "topics": all_topics,
        "entities": all_entities, # located,
    }

    # Add metadata locally using Python.
    ner_dict.update({
        "bulletin_id": bid,
        "bulletin_date": bulletin.get("bulletin_date"),
        "language": LANGUAGE,
        "schema_version": SCHEMA_VERSION,
        "annotation_guideline_version": ANNOTATION_GUIDELINE_VERSION,
        "text": original_text,
        "model": cfg.model,
    })

    # Validate the complete output.
    final_output = NEROutput.model_validate(ner_dict)

    # Final validation against the original bulletin text.
    residual = validate_entity_mentions(
        original_text,
        final_output.model_dump(mode="json")["entities"],
    )

    if residual:
        raise ValueError(
            f"Residual entity errors for {bid}: {residual}"
        )

    return final_output.model_dump(mode="json")


def run(
    input_path: str,
    entity_output_path: str,
    output_path: str,
    limit: int | None = None,
    issue_output_path: str = "data/annotation_issues.jsonl",
):
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-6-luna")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to .env.")

    client = OpenAI(
        # api_key=api_key,
        timeout=180.0,
        # max_retries=0,
    )

    cfg = ApiConfig(client=client, model=model)

    bulletins = read_jsonl(input_path)

    if limit is not None:
        bulletins = bulletins[:limit]

    cached = load_records_by_id(
        entity_output_path)
    done_final = existing_ids(output_path)

    for bulletin in tqdm(bulletins, desc="Annotating bulletins"):

        bid = bulletin['bulletin_id']
        if bid in cached:
            ner_dict = cached[bid]

        else:
            try:
                ner_dict = run_ner_chunk(cfg, bulletin, bid, issue_output_path)
                append_jsonl(entity_output_path, ner_dict)
                cached[bid] = ner_dict
            except Exception as e:
                log_issue(
                    issue_output_path, bid, "NER",
                    [f"{type(e).__name__}: {e}"],
                )
                print(f"NER failed for bulletin {bid}: {e}")
                continue

        if bid in done_final:
            continue


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed_annotations_v2_with_qid_cleaned.jsonl")
    parser.add_argument("--entity-output", default="data/entity_annotations_raw.jsonl")
    parser.add_argument("--output", default="data/annotations_raw.jsonl")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    run(args.input, args.entity_output, args.output, args.limit)