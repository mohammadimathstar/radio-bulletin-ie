
import json
import statistics
import argparse
from typing import Any
from pathlib import Path


# ============================================================
# COMMON FUNCTIONS
# ============================================================

def starts_with_capital(text):
    """Check whether the first alphabetic character is uppercase."""
    for char in text.strip():
        if char.isalpha():
            return char.isupper()
    return False


def reconstruct_lines(words, y_tolerance=0.008):
    """
    Reconstruct text lines from Textract word bounding boxes.

    Expected word format:
        {
            "text": "Example",
            "bbox": [left, top, width, height]
        }

    Coordinates are normalized between 0 and 1.
    """

    words = sorted(
        words,
        key=lambda w: (
            w["bbox"][1] + w["bbox"][3] / 2,
            w["bbox"][0]
        )
    )

    lines = []

    for word in words:
        x, y, width, height = word["bbox"]
        center_y = y + height / 2

        matching_line = None

        for line in lines:
            if abs(line["center_y"] - center_y) <= y_tolerance:
                matching_line = line
                break

        if matching_line is None:
            lines.append({
                "center_y": center_y,
                "words": [word]
            })
        else:
            matching_line["words"].append(word)

            matching_line["center_y"] = statistics.mean(
                w["bbox"][1] + w["bbox"][3] / 2
                for w in matching_line["words"]
            )

    lines.sort(key=lambda line: line["center_y"])

    result = []

    for line in lines:
        line_words = sorted(
            line["words"],
            key=lambda w: w["bbox"][0]
        )

        text = " ".join(
            w["text"] for w in line_words
        )

        left = min(
            w["bbox"][0] for w in line_words
        )

        right = max(
            w["bbox"][0] + w["bbox"][2]
            for w in line_words
        )

        result.append({
            "text": text,
            "left": left,
            "right": right,
            "y": line["center_y"]
        })

    return result


# ============================================================
# IMPLEMENTATION 1
# Detect and join paragraphs in one function
# ============================================================

def join_paragraphs(
    lines,
    indent_threshold=0.025,
    vertical_gap_factor=1.5,
    short_line_gap=0.08
):

    if not lines:
        return ""

    typical_left = statistics.median(
        line["left"] for line in lines
    )

    typical_right = statistics.median(
        line["right"] for line in lines
    )

    gaps = [
        lines[i]["y"] - lines[i - 1]["y"]
        for i in range(1, len(lines))
        if lines[i]["y"] > lines[i - 1]["y"]
    ]

    normal_line_gap = (
        statistics.median(gaps) if gaps else 0
    )

    paragraphs = []
    current_paragraph = lines[0]["text"]

    for i in range(1, len(lines)):

        previous = lines[i - 1]
        current = lines[i]

        # Capital letter condition
        if not starts_with_capital(current["text"]):
            current_paragraph += " " + current["text"]
            continue

        # Rule 1: Indented beginning
        indented = (
            current["left"] >
            typical_left + indent_threshold
        )

        # Rule 2: Extra vertical spacing
        vertical_gap = current["y"] - previous["y"]

        extra_spacing = (
            normal_line_gap > 0
            and vertical_gap >
            normal_line_gap * vertical_gap_factor
        )

        # Rule 3: Previous line is substantially shorter
        short_previous_line = (
            previous["right"] <
            typical_right - short_line_gap
        )

        # Combine the three rules
        new_paragraph = (
            indented
            or extra_spacing
            or short_previous_line
        )

        if new_paragraph:
            paragraphs.append(current_paragraph)
            current_paragraph = current["text"]
        else:
            current_paragraph += " " + current["text"]

    paragraphs.append(current_paragraph)

    return "\n\n".join(paragraphs)


def extract_text(docs: dict[str, Any]) -> list[dict]:
    records = []
    for bulletin_id, raw_blocks in docs.items():
        lines = reconstruct_lines(raw_blocks)
        raw_text = join_paragraphs(lines)
        records.append({"bulletin_id": bulletin_id.replace("_", ":"), "text": raw_text})

    return records


def read_jsonl(input_path: str) -> dict[str, Any]:

    with open(input_path, mode='r') as f:
        data = [json.loads(s) for s in f.readlines()]

    return {d['file_name'][:-4]: d['words'] for d in data}

def save_bulletins_to_jsonl(
    bulletins: dict[str, Any],
    output_path: str,
) -> int:
    """Convert a dictionary of Textract bulletin data into a per-document JSONL file."""
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with out_file.open("w", encoding="utf-8") as f:
        for bulletin in bulletins:
            f.write(json.dumps(bulletin, ensure_ascii=False) + "\n")
            count += 1

    print(f"Bulletins are saved in `{output_path}`.")
    return count




# ============================================================
# Entry point
# ============================================================

def run(input_path: str, output_path: str):
    ocr = read_jsonl(input_path)
    bulletins = extract_text(ocr)
    save_bulletins_to_jsonl(bulletins=bulletins, output_path=output_path)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Convert AWS Textract JSON into a per-document JSONL file."
    )

    parser.add_argument(
        "--input",
        type=str,
        default="data/bulletins_dataset.jsonl",
        help="Path to the input AWS Textract JSONL file.",
    )
    parser.add_argument(
        "--raw",
        type=str,
        default="data/bulletins_text_raw.jsonl",
        help="Path to the output JSONL file.",
    )
    args = parser.parse_args()

    run(args.input, args.raw)

    
