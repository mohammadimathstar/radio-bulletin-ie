"""
Batch CLI for the preprocess package.

Subcommands
-----------
    lexicon    build a lexicon from a folder of raw .txt bulletins
    clean      clean one file, print cleaned text + stats + sentences
    batch      clean every .txt in a folder, write JSONL with cleaned text,
               offset_runs, spans, block_starts, sentences, date
    stats      aggregate cleaning stats across a folder, print which rules fire most

Run ``python -m preprocess.cli <subcommand> -h`` for per-subcommand options.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

from .config import CleanConfig
from .lexicon import Lexicon, build_lexicon
from .pipeline import clean
from .sentences import split_sentences


def _iter_raw(path: Path) -> Iterable[tuple[str, str]]:
    """Yield (name, text) for every .txt under path (recursively)."""
    if path.is_file():
        yield path.name, path.read_text(encoding="utf-8", errors="replace")
        return
    for p in sorted(path.rglob("*.txt")):
        yield p.name, p.read_text(encoding="utf-8", errors="replace")


def cmd_lexicon(args: argparse.Namespace) -> int:
    texts = [t for _, t in _iter_raw(Path(args.input))]
    lex = build_lexicon(
        texts,
        min_freq=args.min_freq,
        wordlist=args.wordlist,
        gazetteer=args.gazetteer,
    )
    lex.save(args.out)
    print(f"[lexicon] {len(lex)} words (min_freq={args.min_freq}) -> {args.out}", file=sys.stderr)
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    from .context import entity_context  # local import to keep top-level light
    raw = Path(args.input).read_text(encoding="utf-8", errors="replace")
    lex = Lexicon.load(args.lexicon) if args.lexicon else None
    cfg = CleanConfig(metadata=args.metadata)
    res = clean(raw, cfg=cfg, lexicon=lex)
    print("=" * 70)
    print("CLEANED TEXT:")
    print(res.text)
    print("=" * 70)
    print(f"raw_length={res.raw_length}  cleaned_length={len(res.text)}  date={res.date_in_text}")
    print(f"stats: {json.dumps(res.stats, ensure_ascii=False)}")
    print(f"block_starts (cleaned offsets): {res.block_starts}")
    print(f"spans ({len(res.spans)}):")
    for s in res.spans:
        print(f"  {s.kind:24s} {s.action:8s} raw={s.start:5d}-{s.end:5d}  {s.text!r}")
    print(f"sentences ({len(split_sentences(res))}):")
    for i, sent in enumerate(split_sentences(res)):
        rs, re_ = sent.raw_span(res)
        print(f"  #{i:02d} clean={sent.start:5d}-{sent.end:5d}  raw={rs:5d}-{re_:5d}  {sent.text!r}")
    if args.entity:
        # example: --entity "raw:120,140" or "clean:300,320"
        kind, _, rng = args.entity.partition(":")
        s, _, e = rng.partition(",")
        ctx = entity_context(res, int(s), int(e), span=kind)
        print("entity context:")
        print(json.dumps(ctx.to_dict() if ctx else None, ensure_ascii=False, indent=2))
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    lex = Lexicon.load(args.lexicon) if args.lexicon else None
    cfg = CleanConfig(metadata=args.metadata)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    agg: Counter = Counter()
    with out_path.open("w", encoding="utf-8") as fh:
        for name, raw in _iter_raw(Path(args.input)):
            res = clean(raw, cfg=cfg, lexicon=lex)
            sents = [s.to_dict(res) for s in split_sentences(res)]
            rec = {
                "id": name,
                "date": res.date_in_text,
                "raw_length": res.raw_length,
                "cleaned_length": len(res.text),
                "text": res.text,
                "spans": [s.to_dict() for s in res.spans],
                "block_starts": res.block_starts,
                "sentence_breaks": res.sentence_breaks,
                "sentences": sents,
                "stats": res.stats,
                "offset_runs": res.aligned.to_runs(),
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            agg.update(res.stats)
            n += 1
            if n % 100 == 0:
                print(f"[batch] cleaned {n} files...", file=sys.stderr)
    print(f"[batch] wrote {n} records to {out_path}", file=sys.stderr)
    if args.print_stats:
        print("[batch] aggregated stats:")
        for k, v in agg.most_common():
            print(f"  {k:32s} {v}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    lex = Lexicon.load(args.lexicon) if args.lexicon else None
    cfg = CleanConfig(metadata=args.metadata)
    agg: Counter = Counter()
    n_files = 0
    n_chars_raw = 0
    n_chars_clean = 0
    for _, raw in _iter_raw(Path(args.input)):
        res = clean(raw, cfg=cfg, lexicon=lex)
        agg.update(res.stats)
        n_files += 1
        n_chars_raw += res.raw_length
        n_chars_clean += len(res.text)
    print(f"files:            {n_files}")
    print(f"raw chars:        {n_chars_raw}")
    print(f"cleaned chars:    {n_chars_clean}")
    print(f"compression:      {n_chars_raw - n_chars_clean} chars removed "
          f"({(n_chars_raw - n_chars_clean) / max(n_chars_raw, 1) * 100:.1f}%)")
    print("rule firings (top 30):")
    for k, v in agg.most_common(30):
        print(f"  {k:32s} {v}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="preprocess", description="OCR preprocessing pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_lex = sub.add_parser("lexicon", help="build a word-frequency lexicon from raw .txt files")
    p_lex.add_argument("input", help="folder or single .txt file")
    p_lex.add_argument("out", help="output lexicon path (one word<TAB>count per line)")
    p_lex.add_argument("--min-freq", type=int, default=3)
    p_lex.add_argument("--wordlist", help="optional external wordlist, one word per line")
    p_lex.add_argument("--gazetteer", help="optional gazetteer of names, one per line")
    p_lex.set_defaults(func=cmd_lexicon)

    p_clean = sub.add_parser("clean", help="clean one file and print everything")
    p_clean.add_argument("input")
    p_clean.add_argument("--lexicon")
    p_clean.add_argument("--metadata", choices=["tag", "remove"], default="tag")
    p_clean.add_argument("--entity", help="optional: 'raw:start,end' or 'clean:start,end' to show its sentence context")
    p_clean.set_defaults(func=cmd_clean)

    p_batch = sub.add_parser("batch", help="clean a folder, write JSONL")
    p_batch.add_argument("input")
    p_batch.add_argument("out", help="output .jsonl path")
    p_batch.add_argument("--lexicon")
    p_batch.add_argument("--metadata", choices=["tag", "remove"], default="tag")
    p_batch.add_argument("--print-stats", action="store_true")
    p_batch.set_defaults(func=cmd_batch)

    p_stats = sub.add_parser("stats", help="aggregate cleaning stats across a folder")
    p_stats.add_argument("input")
    p_stats.add_argument("--lexicon")
    p_stats.add_argument("--metadata", choices=["tag", "remove"], default="tag")
    p_stats.set_defaults(func=cmd_stats)

    args = p.parse_args(argv)
    return args.func(args)


def batch_clean(input_path: str, out_path: str, lexicon_path: str | None = None, metadata: str = "tag") -> int:
    """Programmatic entry point: same as `python -m preprocess.cli batch`."""
    args = argparse.Namespace(input=input_path, out=out_path, lexicon=lexicon_path,
                              metadata=metadata, print_stats=False, func=cmd_batch)
    return cmd_batch(args)


def batch_clean_dir(input_path: str, lexicon_path: str | None = None) -> list[dict]:
    """Clean every .txt under input_path and return the records in memory (small corpora only)."""
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
        tmp = fh.name
    batch_clean(input_path, tmp, lexicon_path)
    return [json.loads(line) for line in Path(tmp).read_text(encoding="utf-8").splitlines()]


if __name__ == "__main__":
    sys.exit(main())
