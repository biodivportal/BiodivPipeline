# Module interface

The input/output contract for each module, as wired in
[`workflows/biodivpipeline.nf`](../../workflows/biodivpipeline.nf). Filenames must match
exactly — downstream modules read them by name. Every module also emits `versions.yml`.

## COLUMN_STANDARDISE (WP6)

| Direction | File | Notes |
| --------- | ---- | ----- |
| in | raw input CSV | biodiversity records |
| out | `standardised.csv` | same records, headers mapped to ABCD terms |
| out | `column_mapping.json` | JSON array of `{header, predicted_header, confidence, review_flag}` |

## BIODIV_ANNOTATE (WP2)

| Direction | File | Notes |
| --------- | ---- | ----- |
| in | WP3 `taxonomy_resolved.csv` | the whole dataset + taxonomy columns, from TAXONOMY_CLASSIFY |
| out | `annotated.jsonld` | records with ontology term URIs |
| out | `enriched.csv` | input records plus `*_URI` annotation columns (taxonomy columns carried through) |
| out | `unresolved_terms.csv` | terms that could not be matched |

The record-id column and the columns to annotate come from the module's `schema.json`
(`columns.id` + `annotate_fields`), overridable via the `DATASET_SCHEMA` env var — see
[`modules/local/biodiv_annotate/README.md`](../../modules/local/biodiv_annotate/README.md).

## TAXONOMY_CLASSIFY (WP3)

| Direction | File | Notes |
| --------- | ---- | ----- |
| in | raw input CSV | biodiversity records |
| out | `taxonomy_resolved.csv` | the **whole input dataset** with `llm_*` (land cover) and `taxon_*` (GBIF) columns appended, joined on the record id. Cultivated rows are kept with empty taxonomy fields. |

## OUTLIER_DETECT (WP4)

| Direction | File | Notes |
| --------- | ---- | ----- |
| in | raw input CSV | biodiversity records |
| out | `flagged_records.csv` | one row per input record (row-aligned, no id column); columns include `outlier_detected`, `outlier_severity`, `outlier_primary_detector`, `outlier_primary_field`, `outlier_reason` |

## PROVISIONAL_CONCEPTS (WP5) — skippable

| Direction | File | Notes |
| --------- | ---- | ----- |
| in | `unresolved_terms.csv` | from BIODIV_ANNOTATE |
| out | `provisional_concepts.json` | list under `provisional_concepts` |
| out | `provisional_concepts.csv` | same, tabular |

## RDF_TRANSFORM (WP7) — skippable

| Direction | File | Notes |
| --------- | ---- | ----- |
| in | `dataset` (path) | `standardised.csv` from COLUMN_STANDARDISE |
| in | `schema` (path) | RML mapping (Turtle/JSON-LD) |
| out | `transformed.<ext>` | RDF triples; `<ext>` = `ttl` (default) / `nt` / `jsonld` per `output_format`; published to `rdf/` |
| out | `validate.json` | `/validate` response: `{valid, issues}` |

## ASSEMBLE_DATASET (WP1)

| Direction | File | Notes |
| --------- | ---- | ----- |
| in | `enriched.csv` | base table (already carries the taxonomy columns through WP2) |
| in | `taxonomy_resolved.csv` | joined by id — now vestigial: the taxonomy columns are already in the base, so nothing new is appended |
| in | `flagged_records.csv` | joined by row position (no id column) |
| out | `final_dataset.csv` | base records + taxonomy columns + outlier columns |

## COLLECT_REPORTS (WP1)

| Direction | File | Notes |
| --------- | ---- | ----- |
| in | `column_mapping.json`, `unresolved_terms.csv`, `taxonomy_resolved.csv`, `flagged_records.csv`, `provisional_concepts.json`, `validate.json` | one signal per module (`NO_FILE` placeholder when a step is skipped) |
| out | `pipeline_summary.json` | per-step metrics |
| out | `pipeline_summary.md` | human-readable summary |

## Notes on drift

Module output schemas have changed during development. Two joins are sensitive to it:

- **Taxonomy** output (`taxonomy_resolved.csv`) is the whole input dataset with the `taxon_*` /
  `llm_*` columns appended; the WP1 assembler sniffs the delimiter and detects the id
  column. (The taxonomy join itself is now vestigial — the columns already reach the
  assembler through WP2's `enriched.csv`.)
- **Outlier** output has no id column, so it is joined by row position — valid only while
  every module preserves input order. Asking WP4 for a `record_id` would make this robust.
