# relation_extraction

Relations between the entity mentions of the NER output, classified by JEV. Only the entity TYPE is used (no subtype, no topic). Rewritten from the uploaded
`schemas.py`, `models.py`, `candidate_generation.py`, `jev.py`; `SCHEMA_REVIEW.md` lists what was changed and why (including defects found in the uploaded code).

```bash
python -m relation_extraction schema-check --input data/processed/ner.jsonl            # entity types of the data vs the schema, relations that can never fire
python -m relation_extraction plan --input data/processed/ner.jsonl --limit 5            # dry run: pairs, JEV requests, sizes; no call
python -m relation_extraction extract --input data/processed/ner.jsonl --out data/processed/relations.jsonl --min-probability 0.6 [--compact-options] [--max-sentence-distance 0]
python -m unittest relation_extraction.tests.test_relation_extraction -v                  # 23 tests, fake JEV
```
```python
from relation_extraction import PipelineConfig, extract_bulletin, load_bulletins
from relation_extraction.jev import make_client
client = make_client()                                          # typesafe-sdk, TYPESAFE_API_KEY
for bulletin in load_bulletins("ner.jsonl"):
    record = extract_bulletin(bulletin, client, PipelineConfig(level="fine"))
```

## Pipeline
`io.load_bulletins` (clean the NER mentions) -> `sentences` (sentence spans, mention -> sentence) -> `candidate_generation` (pairs: types, same-entity, distance, context window) ->
`jev` (marked contexts, answer options, batches, calls) -> `decision` (probabilities -> relations). Everything but the calls is plain Python and tested without JEV.
* **Candidates**: a pair needs at least one relation of the schema that fits the two TYPES in either direction (no_relation never counts), the mentions must not be the same entity (same type and
  same normalized name; names up to 4 characters must be identical), must lie within `--max-sentence-distance` sentences (default 1) and `--max-character-distance` characters (default 200).
* **Question**: the pair, its context (the original text with ALL mentions marked `<e id=".." type="..">..</e id="..">`, nesting allowed) and the options: every relation in every direction the types allow,
  symmetric relations once, plus one `no_relation`. Questions of one context share it in the state; up to `--max-questions` (20) per request.
* **Decision**: `probability` = sum over the directions of the best relation; accepted if >= `--min-probability` and ahead of no_relation by `--min-margin`. The record gives `direction_confidence`,
  `p_no_relation`, `margin`, `coarse` and `category` (projection of the fine relation), both mentions with offsets, and the evidence (the context text).

## Output (one JSON line per bulletin)
`bulletin_id`, `bulletin_date`, `schema_level`, `n_mentions`, `n_pairs`, `n_requests`, `n_relations`, `relations` [{pair_id, relation, coarse, category, head {mention_id, text, type, start, end, normalized_name}, tail, probability,
p_no_relation, margin, direction_confidence, selected_option, jev_confidence, evidence {start, end, text}, sentence_ids}], `pairs` (every pair with p_no_relation and the top 4 options: use it to choose thresholds without new calls),
`relations_merged` (with `--merge-duplicates`: one record per entity pair), `stats` (what the loading and the candidate filters dropped).

## What it costs, measured on your sample bulletin (77 mentions after cleaning)
| setting | pairs | requests | characters sent |
|---|---|---|---|
| instructions in every question, full option text (as before) | 242 | 13 | ~1.07M |
| shared instructions (default) | 242 | 13 | ~0.76M |
| + `--compact-options` | 242 | 13 | ~0.47M |
| + `--max-sentence-distance 0` | 149 | 8 | ~0.29M |
Run `plan` on a few bulletins before `extract`. The pairs are mostly Organization-Place (46), Organization-Organization (39), Person-Person (36), Place-Place (34); Person-Person pairs come from name lists.

## Not verified here
JEV was not called: the tests use a fake client with the interface of your code (`system_one(state, questions, model)`, `answer.choice`, `answer.confidence`, `answer.probabilities`).
Two changes in what JEV receives should be compared on a small sample before a full run: the general instructions in the state instead of in every question (`--no-shared-instructions` restores the old form) and
`--compact-options`. The schema changes (SCHEMA_REVIEW.md) are proposals; the old labels convert with `schema.upgrade_legacy_relation`. The evaluation of thresholds against a gold set is the next step
(`pairs` in the output has what it needs).
