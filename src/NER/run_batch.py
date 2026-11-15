
import os
import json
import time
import argparse
from pathlib import Path
from collections import defaultdict

from openai import OpenAI
from dotenv import load_dotenv
from tqdm import tqdm

from src.configs.ner_cfg import ApiConfig
from src.util.io import (
    read_jsonl,
    load_records_by_id,
    append_jsonl,
    existing_ids,
    log_issue,
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

BATCH_ENDPOINT = "/v1/responses"
BATCH_DIR = Path("data/batches")


# =========================================================
# Structured Outputs schema
# =========================================================

def make_strict_schema(schema: dict) -> dict:
    """Prepare a Pydantic JSON schema for strict Structured Outputs."""

    if isinstance(schema, list):
        return [make_strict_schema(item) for item in schema]

    if not isinstance(schema, dict):
        return schema

    schema = {
        key: make_strict_schema(value)
        for key, value in schema.items()
        if key != "default"
    }

    if schema.get("type") == "object":
        properties = schema.get("properties", {})
        schema["required"] = list(properties.keys())
        schema["additionalProperties"] = False

    return schema


def get_ner_schema():
    schema = NERExtraction.model_json_schema()
    return make_strict_schema(schema)


# =========================================================
# Prepare Batch requests
# =========================================================

def prepare_batch_requests(
    cfg: ApiConfig,
    bulletins: list,
    cached_ids: set,
    done_final: set,
):
    """
    Create one Batch request per text chunk.

    The manifest keeps the original bulletin ID, chunk index,
    global offset and chunk text.
    """

    requests = []
    manifest = []

    schema = get_ner_schema()

    for bulletin in tqdm(bulletins, desc="Preparing batch"):

        bid = bulletin["bulletin_id"]

        if bid in cached_ids or bid in done_final:
            continue

        original_text = bulletin["text"]

        chunks = chunk_text(
            original_text,
            MAX_CHUNK_CHARS,
        )

        for chunk_index, (global_offset, chunk) in enumerate(chunks):

            custom_id = f"{bid}_chunk_{chunk_index}"

            chunk_bulletin = {
                **bulletin,
                "text": chunk,
            }

            payload = build_entity_input(chunk_bulletin)

            requests.append({
                "custom_id": custom_id,
                "method": "POST",
                "url": BATCH_ENDPOINT,
                "body": {
                    "model": cfg.model,
                    "instructions": ENTITY_SYSTEM_PROMPT,
                    "input": payload,
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": "ner_extraction",
                            "strict": True,
                            "schema": schema,
                        }
                    },
                },
            })

            manifest.append({
                "custom_id": custom_id,
                "bulletin_id": bid,
                "chunk_index": chunk_index,
                "global_offset": global_offset,
                "chunk_text": chunk,
            })

    return requests, manifest


def write_batch_jsonl(path: Path, records: list):
    """Write Batch requests or manifest records to JSONL."""

    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(
                json.dumps(record, ensure_ascii=False) + "\n"
            )


# =========================================================
# Submit Batch
# =========================================================

def submit_batch(
    cfg: ApiConfig,
    bulletins: list,
    entity_output_path: str,
    output_path: str,
):
    """Prepare, upload and submit a Batch job."""

    cached = load_records_by_id(entity_output_path)
    done_final = existing_ids(output_path)

    requests, manifest = prepare_batch_requests(
        cfg,
        bulletins,
        set(cached.keys()),
        done_final,
    )

    if not requests:
        print("No new bulletins to process.")
        return

    if len(requests) > 50_000:
        raise ValueError(
            "Batch contains more than 50,000 requests. "
            "Split it into multiple batches."
        )

    BATCH_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")

    request_path = BATCH_DIR / f"requests_{timestamp}.jsonl"
    manifest_path = BATCH_DIR / f"manifest_{timestamp}.jsonl"

    write_batch_jsonl(request_path, requests)
    write_batch_jsonl(manifest_path, manifest)

    print(f"Prepared {len(requests)} chunk requests.")

    # Upload request file.
    with request_path.open("rb") as f:
        uploaded_file = cfg.client.files.create(
            file=f,
            purpose="batch",
        )

    # Submit Batch.
    batch = cfg.client.batches.create(
        input_file_id=uploaded_file.id,
        endpoint=BATCH_ENDPOINT,
        completion_window="24h",
        metadata={
            "task": "bulletin_ner",
            "schema_version": SCHEMA_VERSION,
        },
    )

    # Save the information needed for collection.
    state = {
        "batch_id": batch.id,
        "manifest_path": str(manifest_path),
        "entity_output_path": entity_output_path,
        "output_path": output_path,
        "model": cfg.model,
    }

    state_path = BATCH_DIR / f"{batch.id}.json"

    with state_path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    print("\nBatch submitted.")
    print(f"Batch ID: {batch.id}")
    print(f"Status: {batch.status}")
    print(f"Requests: {len(requests)}")
    print(f"Manifest: {manifest_path}")


# =========================================================
# Check Batch status
# =========================================================

def check_batch(cfg: ApiConfig, batch_id: str):
    """Check the current status of a Batch job."""

    batch = cfg.client.batches.retrieve(batch_id)

    print(f"\nBatch ID: {batch.id}")
    print(f"Status: {batch.status}")

    if batch.request_counts:
        print(f"Total: {batch.request_counts.total}")
        print(f"Completed: {batch.request_counts.completed}")
        print(f"Failed: {batch.request_counts.failed}")

    if batch.output_file_id:
        print(f"Output file: {batch.output_file_id}")

    if batch.error_file_id:
        print(f"Error file: {batch.error_file_id}")

    return batch


# =========================================================
# Parse Batch results
# =========================================================

def extract_response_text(body: dict) -> str:
    """Extract structured output from a Responses API response."""

    if body.get("status") != "completed":
        raise RuntimeError(
            f"Response status: {body.get('status')}"
        )

    for item in body.get("output", []):

        if item.get("type") != "message":
            continue

        for content in item.get("content", []):

            if content.get("type") == "refusal":
                raise RuntimeError(
                    f"Model refusal: {content.get('refusal')}"
                )

            if content.get("type") == "output_text":
                return content["text"]

    raise RuntimeError("No structured output found.")


def parse_batch_results(cfg: ApiConfig, batch):
    """
    Download and parse successful Batch results.

    Returns:
        results: custom_id -> NERExtraction
        failures: custom_id -> error message
    """

    results = {}
    failures = {}

    if batch.output_file_id:

        response = cfg.client.files.content(
            batch.output_file_id
        )

        for line in response.text.splitlines():

            if not line.strip():
                continue

            record = json.loads(line)
            custom_id = record["custom_id"]

            try:
                if record.get("error"):
                    raise RuntimeError(str(record["error"]))

                api_response = record["response"]

                if api_response["status_code"] != 200:
                    raise RuntimeError(
                        f"HTTP {api_response['status_code']}"
                    )

                response_text = extract_response_text(
                    api_response["body"]
                )

                extraction = NERExtraction.model_validate_json(
                    response_text
                )

                results[custom_id] = extraction

            except Exception as e:
                failures[custom_id] = (
                    f"{type(e).__name__}: {e}"
                )

    # Read request-level failures from the error file.
    if batch.error_file_id:

        response = cfg.client.files.content(
            batch.error_file_id
        )

        for line in response.text.splitlines():

            if not line.strip():
                continue

            record = json.loads(line)
            custom_id = record["custom_id"]

            failures[custom_id] = str(
                record.get("error", "Batch request failed")
            )

    return results, failures


# =========================================================
# Merge chunk results
# =========================================================

def merge_chunk_results(
    cfg: ApiConfig,
    bulletin: dict,
    chunk_manifest: list,
    chunk_results: dict,
    bid,
) -> dict:
    """Merge chunk-level results into a bulletin-level NER output."""

    original_text = bulletin["text"]

    all_entities = []
    all_topics = []

    chunk_manifest = sorted(
        chunk_manifest,
        key=lambda x: x["chunk_index"],
    )

    for item in chunk_manifest:

        custom_id = item["custom_id"]

        chunk = item["chunk_text"]
        global_offset = item["global_offset"]

        extraction = chunk_results[custom_id]

        chunk_dict = extraction.model_dump(mode="json")

        # Merge topics.
        for topic in chunk_dict["topics"]:
            if topic not in all_topics:
                all_topics.append(topic)

        # Validate entity types.
        entities = validate_entity_types(
            chunk_dict["entities"]
        )

        # Correct chunk-local offsets.
        entities = correct_llm_offsets(
            chunk,
            entities,
        )

        # Convert to original bulletin offsets.
        for entity in entities:

            if (
                entity.get("start") is None
                or entity.get("end") is None
            ):
                print(
                    f"WARNING: Missing offsets in {bid}: "
                    f"{entity.get('id')} - {entity.get('text')!r}"
                )
                continue

            entity["start"] += global_offset
            entity["end"] += global_offset

            entity["id"] = f"e{len(all_entities) + 1}"

            # Namespace event IDs by chunk.
            if entity.get("type") == "Event" and entity.get("event_id"):
                entity["event_id"] = (
                    f"chunk_{item['chunk_index'] + 1}_"
                    f"{entity['event_id']}"
                )

            all_entities.append(entity)

    ner_dict = {
        "topics": all_topics,
        "entities": all_entities,
        "bulletin_id": bid,
        "bulletin_date": bulletin.get("bulletin_date"),
        "language": LANGUAGE,
        "schema_version": SCHEMA_VERSION,
        "annotation_guideline_version": ANNOTATION_GUIDELINE_VERSION,
        "text": original_text,
        "model": cfg.model,
    }

    # Validate complete output.
    final_output = NEROutput.model_validate(ner_dict)

    # Final mention validation.
    final_dict = final_output.model_dump(mode="json")

    residual = validate_entity_mentions(
        original_text,
        final_dict["entities"],
    )

    if residual:
        raise ValueError(
            f"Residual entity errors for {bid}: {residual}"
        )

    return final_dict


# =========================================================
# Collect Batch results
# =========================================================

def read_manifest_jsonl(path):
    records = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    return records

def collect_batch(
    cfg: ApiConfig,
    batch_id: str,
    input_path: str,
    issue_output_path: str,
):
    """Collect Batch results and save validated bulletin annotations."""

    batch = check_batch(cfg, batch_id)

    if batch.status != "completed":
        raise RuntimeError(
            f"Batch is not completed: {batch.status}"
        )

    state_path = BATCH_DIR / f"{batch_id}.json"

    if not state_path.exists():
        raise FileNotFoundError(state_path)

    with state_path.open("r", encoding="utf-8") as f:
        state = json.load(f)

    # Load manifest.
    # manifest = read_jsonl(state["manifest_path"])
    manifest = read_manifest_jsonl(state["manifest_path"])

    # Load original bulletins.
    bulletins = read_jsonl(input_path)

    bulletin_by_id = {
        b["bulletin_id"]: b
        for b in bulletins
    }

    # Download and parse Batch responses.
    chunk_results, failures = parse_batch_results(
        cfg,
        batch,
    )

    print(f"\nSuccessful chunks: {len(chunk_results)}")
    print(f"Failed chunks: {len(failures)}")

    # Group manifest entries by bulletin.
    grouped = defaultdict(list)

    for item in manifest:
        grouped[item["bulletin_id"]].append(item)

    entity_output_path = state["entity_output_path"]

    cached = load_records_by_id(entity_output_path)
    done_final = existing_ids(state["output_path"])

    successful = 0
    failed = 0

    for bid, chunk_items in tqdm(
        grouped.items(),
        desc="Merging annotations",
    ):

        if bid in cached or bid in done_final:
            continue

        # All chunks must succeed before merging.
        missing = [
            item["custom_id"]
            for item in chunk_items
            if item["custom_id"] not in chunk_results
        ]

        if missing:

            reasons = [
                f"{cid}: {failures.get(cid, 'Missing result')}"
                for cid in missing
            ]

            log_issue(
                issue_output_path,
                bid,
                "NER",
                reasons,
            )

            failed += 1
            continue

        try:

            ner_dict = merge_chunk_results(
                cfg=cfg,
                bulletin=bulletin_by_id[bid],
                chunk_manifest=chunk_items,
                chunk_results=chunk_results,
                bid=bid,
            )

            # Use your existing JSONL writer.
            append_jsonl(
                entity_output_path,
                ner_dict,
            )

            cached[bid] = ner_dict

            successful += 1

        except Exception as e:

            log_issue(
                issue_output_path,
                bid,
                "NER",
                [f"{type(e).__name__}: {e}"],
            )

            print(f"NER failed for bulletin {bid}: {e}")

            failed += 1

    print("\nCollection finished.")
    print(f"Successful bulletins: {successful}")
    print(f"Failed bulletins: {failed}")


# =========================================================
# Main
# =========================================================

def run(
    input_path: str,
    entity_output_path: str,
    output_path: str,
    limit: int | None = None,
):
    """Submit a Batch job."""

    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")

    model = os.getenv(
        "OPENAI_MODEL",
        "gpt-6-luna",
    )

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Add it to .env."
        )

    client = OpenAI(
        api_key=api_key,
        timeout=180.0,
    )

    cfg = ApiConfig(
        client=client,
        model=model,
    )

    bulletins = read_jsonl(input_path)

    if limit is not None:
        bulletins = bulletins[:limit]

    submit_batch(
        cfg,
        bulletins,
        entity_output_path,
        output_path,
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "command",
        choices=["submit", "status", "collect"],
    )

    parser.add_argument(
        "--input",
        default="data/preprocessed/bulletins_processed.jsonl",
    )

    parser.add_argument(
        "--entity-output",
        default="data/entity_annotations_raw.jsonl",
    )

    parser.add_argument(
        "--output",
        default="data/annotations_raw.jsonl",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--batch-id",
        default=None,
    )

    parser.add_argument(
        "--issues",
        default="data/annotation_issues.jsonl",
    )

    args = parser.parse_args()

    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")

    model = os.getenv(
        "OPENAI_MODEL",
        "gpt-6-luna",
    )

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    client = OpenAI(
        api_key=api_key,
        timeout=180.0,
    )

    cfg = ApiConfig(
        client=client,
        model=model,
    )

    if args.command == "submit":

        bulletins = read_jsonl(args.input)

        if args.limit is not None:
            bulletins = bulletins[:args.limit]

        submit_batch(
            cfg,
            bulletins,
            args.entity_output,
            args.output,
        )

    elif args.command == "status":

        if not args.batch_id:
            parser.error("--batch-id is required.")

        check_batch(
            cfg,
            args.batch_id,
        )

    elif args.command == "collect":

        if not args.batch_id:
            parser.error("--batch-id is required.")

        collect_batch(
            cfg,
            args.batch_id,
            args.input,
            args.issues,
        )


if __name__ == "__main__":
    main()
