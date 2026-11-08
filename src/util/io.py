import json
from pathlib import Path

from src.NER.models.bulletins import BulletinInput


def read_jsonl(path: str) -> list[dict]:
    records: list[dict] = []
    ids: set[str] = set()
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            raw = json.loads(line)
            record = BulletinInput(
                bulletin_id=raw["id"],
                text=raw["text"],
            )
            if record.bulletin_id in ids:
                raise ValueError(
                    f"Duplicate bulletin_id {record.bulletin_id} at line {line_no}"
                )
            ids.add(record.bulletin_id)
            records.append(record.model_dump())
    return records


def load_records_by_id(path: str, bulletin_id_col: str = "bulletin_id") -> dict[str, dict]:
    by_id: dict[str, dict] = {}
    if not Path(path).exists():
        return by_id
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            by_id[rec[bulletin_id_col]] = rec
    return by_id


def existing_ids(path: str) -> set[str]:
    return set(load_records_by_id(path).keys())


def append_jsonl(path: str, obj: dict):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def log_issue(path: str, bulletin_id: str, stage: str, issues):
    append_jsonl(path, {
        "bulletin_id": bulletin_id,
        "stage": stage,
        "status": "needs_review",
        "issues": issues,
    })


if __name__ == "__main__":
    p = "data/processed_annotations_v2_with_qid_cleaned.jsonl"

    pp = read_jsonl(p)

    from langchain_core.prompts import PromptTemplate

    # # Define the template once globally
    prompt_template = PromptTemplate.from_template(
        "Date: {bulletin_date}\nText: {text}"
    )

    final_prompt = prompt_template.format(**pp[0])
    print(final_prompt)

    print(type(json.dumps(pp[0], ensure_ascii=False)))