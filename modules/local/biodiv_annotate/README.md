# BiodivPortal Annotator (WP2)

Annotates biodiversity CSV records against the [BiodivPortal](https://data.biodivportal.gfbio.org/annotator)
ontologies. For each record it collects the unique terms from a configurable set of
columns, sends them to the annotator API, and writes back the same records with a `*_URI`
column appended after each annotated field.

Part of the BiodivPipeline project, where it runs as the `BIODIV_ANNOTATE` Nextflow module.

---

## Quickstart

**Prerequisites:** Docker, and a BiodivPortal API key.

```bash
docker build -t ghcr.io/biodivportal/biodiv-annotate:0.1 .
docker run --rm \
  -e BIODIV_API_KEY='<your key>' \
  -v "$PWD/data:/data" \
  ghcr.io/biodivportal/biodiv-annotate:0.1 \
  python /app/bin/annotate_biodiv.py --input /data/sample.csv --out-enriched-csv /data/enriched.csv
```

Outputs are written next to the input (`./data` is mounted at `/data`).

### Run the NF pipeline test
From the repo root:
```bash
nf-test test modules/local/biodiv_annotate/tests/main.nf.test
```

---

## Input

A CSV of biodiversity records. The record-id column and the columns to annotate are **not
hard-coded** — they come from a schema file so the module works with other datasets:

```json
{
  "columns": { "id": "HerbariumID" },
  "annotate_fields": [
    "FullNameCache", "NameCache", "Genus", "Family", "Locality",
    "FundortUNdOeko", "Country", "TitelEtikett", "Expeditionsangabe"
  ]
}
```

- `columns.id` is the record identifier used to key annotations back to rows.
- `annotate_fields` is the default set of columns sent to the annotator; the `--columns`
  CLI arg overrides it per run.

The BGBM schema ships with the image as `bin/schema.json`. To use another dataset, point
`DATASET_SCHEMA` at your schema file (or replace the default and rebuild the image).

> **Limitation:** the category hints and `example_*` columns in `unresolved_terms.csv`
> still reference the original BGBM field names. They are output formatting and do not
> affect which records get annotated; only `columns.id` and `annotate_fields` are
> schema-driven.

### Environment

| Variable | Default | Purpose |
|---|---|---|
| `BIODIV_API_KEY` | — | **Required.** BiodivPortal annotator key. In the pipeline this is aliased from the `WP2_BIODIV_API_KEY` Nextflow secret. |
| `DATASET_SCHEMA` | baked-in `bin/schema.json` | Absolute path to a dataset schema file. Set only when using a different dataset. |

### CLI arguments

| Argument | Purpose |
|---|---|
| `--input` | Path to the input CSV |
| `--out-json` | JSON-LD annotation output (one record per input row) |
| `--out-enriched-csv` | The input records plus a `*_URI` column after each annotated field |
| `--out-unresolved` | Terms that could not be matched, aggregated with counts + examples |
| `--out-wp5-unresolved-rows` | Per-record unresolved rows fed to WP5 (provisional concepts) |
| `--max-rows` | Cap on the number of rows annotated. In the pipeline this comes from `params.max_rows`. |
| `--columns` | Override the `annotate_fields` to annotate for this run |
| `--target-ontologies` | Per-column ontology filters, `COLUMN:ONTOLOGY ...` |

---

## Output

- **`annotated.jsonld`** — JSON-LD graph of the annotations per record.
- **`enriched.csv`** — the input records with a `<Field>_URI` column inserted after each
  annotated field (empty when no match). Original columns and order are preserved.
- **`unresolved_terms.csv`** — terms with no annotation, aggregated by
  `(field, normalized_term, reason)` with occurrence counts and example values.

---

## How it works

1. Read up to `--max-rows` records.
2. Collect the unique normalized terms from `annotate_fields` across all records.
3. Annotate each unique term once (concurrent, with retries) via the BiodivPortal API.
4. Build per-record annotations (deduplicated) and the unresolved terms list.
5. Write `enriched.csv` (records + `*_URI`), `annotated.jsonld`, and `unresolved_terms.csv`.
