"""Run OCR-to-text and text preprocessing in sequence.

Step 1 — ``ocr2text.py``:           Textract JSONL → raw text JSONL
Step 2 — ``preprocess_bulletins.py``: raw text JSONL → cleaned text JSONL

All arguments are collected here; each script is imported and its ``run()``
function called directly (no subprocess).

Usage:
    python run_ocr_pipeline.py \\
        --input    data/bulletins_dataset.jsonl \\
        --raw      data/bulletins_text_raw.jsonl \\
        --output   data/bulletins_text_cleaned.jsonl \\
        --lex_path data/anp_lexicon.txt

    # re-clean only (skip OCR, reuse an existing raw file):
    python run_ocr_pipeline.py --skip-ocr
"""
import argparse
import sys
from pathlib import Path

# make the sibling scripts importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ocr2text import run as run_ocr
from clean_text import run as run_preprocess


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run OCR-to-text and text preprocessing in sequence.",
    )
    parser.add_argument(
        "--input", type=str, default="data/bulletins_dataset.jsonl",
        help="Path to the input AWS Textract JSONL file (step 1 input).",
    )
    parser.add_argument(
        "--raw", type=str, default="data/bulletins_text_raw.jsonl",
        help="Path to the intermediate raw-text JSONL file "
             "(step 1 output / step 2 input).",
    )
    parser.add_argument(
        "--output", type=str, default="data/bulletins_text_cleaned.jsonl",
        help="Path to the cleaned-text JSONL file (step 2 output).",
    )
    parser.add_argument(
        "--lex_path", type=str, default="data/anp_lexicon.txt",
        help="Path to the lexicon file (built from the corpus on first run).",
    )
    parser.add_argument(
        "--skip-ocr", action="store_true",
        help="Skip step 1 and reuse an existing raw file (re-clean only).",
    )
    args = parser.parse_args()

    # ---- Step 1: OCR → raw text ----
    if args.skip_ocr:
        if Path(args.raw).exists():
            print(f"Skipping OCR; reusing {args.raw}")
        else:
            print(f"✗ --skip-ocr given but `{args.raw}` does not exist.")
            sys.exit(1)
    else:
        print("Step 1: OCR → raw text")
        run_ocr(args.input, args.raw)

    # ---- Step 2: raw text → cleaned text ----
    print("\nStep 2: raw text → cleaned text")
    run_preprocess(args.raw, args.output, args.lex_path)

    print(f"\n✓ Done → {args.output}")


if __name__ == "__main__":
    main()