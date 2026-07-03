# WP1 Hardening Plan

Follow-up work for the BiodivPipeline (WP1). WP2–WP8 internals belong to other teams;
everything here is WP1-owned. Target: meet Lastenheft Requirement 1.

**Branching:** one short-lived branch per task off `dev`, small PRs. `A → F → B` are
coupled (same files) and stay on one branch. No CI — run tests manually.

## Status
- Outputs **(i)** `final_dataset.csv` and **(iii)** `pipeline_summary.{json,md}` — done, on `wp1-enhancement-reports`.
- Output **(ii)** RDF — blocked on WP7 (stub); WP1 owns only the wiring.

## Tasks

| ID | Task | Difficulty | Depends on |
| -- | ---- | ---------- | ---------- |
| A | Move `collect_reports.py` + `assemble_dataset.py` to pipeline-level `bin/` so Nextflow hashes them (fixes `-resume` not re-running on script edits). Shebang + `chmod +x` + call by bare name; update both module `main.nf`. | Medium | — |
| F | Row-count guard in `assemble_dataset`: on mismatch, **warn + omit** quality columns (never guess) and set `quality_join: "skipped"` in the summary. Prefer id-join when available. | Easy | A |
| B | `pytest` in `tests/python/` for both scripts, with fixtures for **current + legacy** schemas (WP6 list/dict, WP3 `;`/`,`, WP4 `outlier_*`/`issue_type`). Run manually. | Medium | A, F |
| C | Minimal DwC-A input: a `DWCA_EXTRACT` front module that turns a `.zip` archive's occurrence core into CSV, then feeds `COLUMN_STANDARDISE`. Defer extensions/multi-core. | Hard | — |
| D | Run `nf-core lint`, fix easy findings, list the rest. | Easy→Med | — |
| E1 | Containerise our two modules (`assemble_dataset`, `collect_reports`) with a slim `python` image; add `container` directives. | Medium | A |
| G | One concise `docs/module-interfaces.md`: per consumed output → filename, delimiter, key fields, record-id (or "positional"). Retire the vague "interface spec" mention in `output.md`. | Easy | — |
| H | Update README/usage: docker profile works; document `-profile test,docker,emulate_amd64` for Apple Silicon; drop the "does not work yet" note. | Easy | — |
| I | `mapping_schema`: warn + continue on the empty placeholder; add `--require_mapping_schema` (default `false`); record `rdf.mapping_schema: "placeholder"` in the summary. | Easy | — |

## Parallelisable now (no file overlap, good for helpers)
**G, H, D, I** — one branch each.

## Sequenced (senior)
`A → F → B` on one branch, then **E1** after A merges, then **C**.

## Cross-team asks (lead)
- Ask **WP4** to emit a `record_id` in `flagged_records.csv` (makes the quality join robust; retires the positional fallback).
- Move demo images off `ghcr.io/mitchell7970/…` to the org registry.

## Design decisions (settled)
- Scripts stay **host-run** but hashed via `bin/` (A). Containers (E1) come later.
- Tests are **pytest-first** (logic), one thin `nf-test` per module later; no full-pipeline test yet.
- Quality join: **warn + omit** on mismatch, id-join preferred.
- `mapping_schema`: **warn + continue**, fail-fast behind a flag.
- DwC-A: **minimal occurrence-core** extraction only.
- Interfaces doc: **one consolidated markdown**, no JSON Schema yet.
