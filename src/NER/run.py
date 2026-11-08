from openai import OpenAI
import os
from dotenv import load_dotenv
from tqdm import tqdm
import argparse

from src.configs.ner_cfg import ApiConfig
from .prompts.entity_extraction import ENTITY_SYSTEM_PROMPT, build_entity_input
from .models.bulletins import NEROutput
from src.util.io import (
    read_jsonl, load_records_by_id, append_jsonl, 
    existing_ids, log_issue
)
from .validate import validate_entity_types, validate_entity_mentions
from src.util.correct_llm import correct_llm_offsets


LOCATED_STATUSES = ("exact_normalized", "fuzzy")



def call_parse(cfg: ApiConfig, instructions, payload, response_model) -> NEROutput:
    """Call the Responses API with Structured Outputs (Pydantic via text_format)."""
    kwargs = dict(
        model=cfg.model,
        instructions=instructions,
        input=payload,
        text_format=response_model,
    )
    response = cfg.client.responses.parse(**kwargs)
    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError(f"No parsed output. Raw response: {response.output_text}")
    return parsed


def run_ner(cfg: ApiConfig, bulletin: dict, bid, issue_output_path: str) -> dict:
    """Run the NER pipeline with the given configuration and input."""
    
    parsed = call_parse(
        cfg, 
        ENTITY_SYSTEM_PROMPT, 
        build_entity_input(bulletin), 
        NEROutput)
    ner_dict = parsed.model_dump(mode="json")

    ner_dict["entities"] = validate_entity_types(ner_dict["entities"])
    ner_dict["entities"] = correct_llm_offsets(bulletin["text"], ner_dict["entities"])
        
    # Keep only entities whose offsets could be confidently located. Entities
    # whose surface form is not an exact substring of the text (or that occur
    # ambiguously) are dropped and logged, but they no longer abort the run.
    located: list[dict] = []
    dropped: list[dict] = []
    for e in ner_dict["entities"]:
        if e.get("offset_method") in LOCATED_STATUSES:
            e.pop("offset_method", None)  # diagnostic, not part of the schema
            located.append(e)
        else:
            dropped.append(e)
    ner_dict["entities"] = located

    if dropped:
        log_issue(
            issue_output_path, bid, "NER",
            [f"dropped {len(dropped)} unlocatable entities: "
             + ", ".join(e["id"] for e in dropped)],
        )

    # Stamp ground-truth fields from the input.
    ner_dict["bulletin_id"] = bid
    ner_dict["bulletin_date"] = bulletin["bulletin_date"]
    ner_dict["text"] = bulletin["text"]

    # Safety net: surviving entities are guaranteed to match, so this should
    # be empty. If it is not, something is genuinely wrong -> raise.
    residual = validate_entity_mentions(bulletin["text"], ner_dict["entities"])
    if residual:
        raise ValueError(f"Residual entity errors for {bid}: {residual}")

    return ner_dict



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

    client = OpenAI(api_key=api_key, max_retries=3, timeout=50)

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
    parser.add_argument("--limit", type=int, default=1)
    args = parser.parse_args()
    run(args.input, args.entity_output, args.output, args.limit)