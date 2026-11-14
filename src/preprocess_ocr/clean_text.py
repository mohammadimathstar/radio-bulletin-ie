#!/usr/bin/env python3
"""Preprocess bulletins from a JSONL file with entity annotations.

For each bulletin line:
  - text  -> text_org  (the raw text),  text  = the cleaned text
  - each entity: name / start / end -> name_org / start_org / end_org (the raw values),
                and the new name / start / end are recomputed in the CLEANED text:
                    cs = res.clean_span(start_org, end_org)   # (clean_start, clean_end) or None
                    name  = res.text[cs[0]:cs[1]]              # the surface form after cleaning
                If the entity fell entirely inside content that was removed by cleaning
                (a stripped number line, filler, etc.), name/start/end become null and the
                *_org fields still hold the original values -- nothing is lost.

Everything else on the bulletin (id, created_at, updated_at, entities[*].id/label/qid)
is left untouched.

Usage:
    python scripts/preprocess_jsonl.py [INPUT.jsonl] [OUTPUT.jsonl] [LEXICON.txt]

Defaults:
    INPUT   = data/processed_annotations_v2_with_qid.jsonl
    OUTPUT  = download/processed_annotations_v2_cleaned.jsonl
    LEXICON = download/anp_lexicon.txt   (built from the corpus on first run)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
import argparse


# make `preprocess` importable whether the script is run from the project root or elsewhere
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from preprocess import build_lexicon, clean, CleanConfig, Lexicon


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if ln:
                yield json.loads(ln)


def run(raw_path: str, output_path: str, lex_path: str) -> None:
    """Clean raw bulletin text and write the cleaned version to JSONL."""

    in_path = Path(raw_path)
    out_path = Path(output_path)
    lex_path = Path(lex_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # keep section/bulletin headers in the text (useful as sentence-boundary markers);
    # switch to "remove" if you'd rather they were stripped.
    cfg = CleanConfig(metadata="tag")

    # ---- 1. lexicon (load if present, otherwise build from the whole corpus) ----
    if lex_path.exists():
        lex = Lexicon.load(str(lex_path))
        print(f"loaded lexicon ({len(lex)} words) from {lex_path}")
    else:
        print(f"building lexicon from {in_path} ...")
        lex = build_lexicon((r.get("text", "") for r in iter_jsonl(in_path)), min_freq=3)
        lex.save(str(lex_path))
        print(f"built lexicon ({len(lex)} words) -> {lex_path}")

    # ---- 2. clean each bulletin and remap its entity spans ----
    n = n_ent = n_dropped = n_bad = 0
    agg: Counter = Counter()
    out_path.unlink(missing_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for rec in iter_jsonl(in_path):
            raw_text = rec.get("text", "") or ""
            res = clean(raw_text, cfg=cfg, lexicon=lex)

            # rename top-level text: keep the raw under text_org, put cleaned under text
            rec["text_org"] = raw_text
            rec["text"] = res.text            

            agg.update(res.stats)
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
            if n % 100 == 0:
                print(f"  ... {n} bulletins processed")

    # ---- 3. report ----
    print(f"\nDone.")
    print(f"  bulletins in   : {n}")
    print(f"  entities mapped: {n_ent}")
    print(f"  entities dropped (in removed content): {n_dropped}")
    print(f"  entities with bad/missing spans      : {n_bad}")
    print(f"  output          : {out_path}")
    print(f"\nRule firings across the corpus:")
    for k, v in agg.most_common():
        print(f"  {k:35s} {v:>8d}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Preprocess bulletin texts."
    )
    parser.add_argument(
        "--input", type=str, default="data/bulletins_text_raw.jsonl",
        help="Path to the raw bulletin texts in a JSONL file.",
    )
    parser.add_argument(
        "--lex_path", type=str, default="data/anp_lexicon.txt",
        help="Path to the lexicon file.",
    )
    parser.add_argument(
        "--output", type=str, default="data/bulletins_text_cleaned.jsonl",
        help="Path to the output JSONL file.",
    )
    args = parser.parse_args()
    run(args.input, args.output, args.lex_path)