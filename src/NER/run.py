from openai import OpenAI
import os
from dotenv import load_dotenv
from tqdm import tqdm
import argparse

from src.configs.ner_cfg import ApiConfig
from .prompts.entity_extraction import ENTITY_SYSTEM_PROMPT, build_entity_input
from .models.bulletins import NEROutput, NERExtraction
from src.util.io import (
    read_jsonl, load_records_by_id, append_jsonl, 
    existing_ids, log_issue
)
from .validate import validate_entity_types, validate_entity_mentions
from src.util.correct_llm import correct_llm_offsets


LOCATED_STATUSES = ("exact_normalized", "fuzzy", "exact_raw")
SCHEMA_VERSION = "1.0"
ANNOTATION_GUIDELINE_VERSION = "1.0"
LANGUAGE = "nl"


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

    print(ner_dict['entities'])

    print("LOCATED_STATUSES:", LOCATED_STATUSES)
    print("Type:", type(LOCATED_STATUSES))
        
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
                ner_dict = run_ner(cfg, bulletin, bid, issue_output_path)
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