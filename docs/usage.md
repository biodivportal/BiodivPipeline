# BiodivPipeline: Usage

## Prerequisites

| Requirement                          | Minimum | Tested          |
| ------------------------------------ | ------- | --------------- |
| Java                                 | 11+     | OpenJDK 21.0.11 |
| [Nextflow](https://www.nextflow.io/) | >= 25.10.4 | 26.04.0         |
| [Docker](https://www.docker.com/)    | >= 20.x | 29.3.0          |

### Secrets

The pipeline reads four API keys as **Nextflow secrets**. All four must be set before a `test` or `docker` run, otherwise the run stops with `Required secret is missing: '<NAME>'`.

| Secret               | Used by                              | What it is                                       |
| -------------------- | ------------------------------------ | ------------------------------------------------ |
| `WP2_BIODIV_API_KEY` | WP2 annotation (`biodiv_annotate`)   | BiodivPortal Annotator API key                   |
| `WP3_OPENAI_API_KEY` | WP3 taxonomy (`taxonomy_classify`)   | OpenAI key for land-cover / taxonomy classification |
| `WP4_OPENAI_API_KEY` | WP4 outlier detection (`outlier_detect`) | OpenAI key for the LLM outlier detector          |
| `WP5_OPENAI_API_KEY` | WP5 provisional concepts (`provisional_concepts`) | OpenAI key for the provisional concepts resolver |

Set each one once (stored under `~/.nextflow`, per user — never committed to the repo):

```bash
nextflow secrets set WP2_BIODIV_API_KEY "<BiodivPortal key>"
nextflow secrets set WP3_OPENAI_API_KEY "<OpenAI key>"
nextflow secrets set WP4_OPENAI_API_KEY "<OpenAI key>"
nextflow secrets set WP5_OPENAI_API_KEY "<OpenAI key>"
```

Notes:

- The OpenAI keys have **different names** on purpose (WP3, WP4, and WP5 keep separate keys); you may set the same value for all of them.
- Keys are read via `nextflow secrets set`, **not** shell `export`. The names are WP-prefixed — the old un-prefixed names (`BIODIV_API_KEY`, `OPENAI_API_KEY`) and the `export VAR=...` method no longer work. Each module re-aliases its secret to the env var its code expects, so no key ever needs to be exported by hand.

## Input data

The pipeline expects a CSV file with biodiversity specimen records and a header row. Column names do not need to follow any specific standard — the first pipeline module is responsible for mapping headers to a target schema.

A small real sample dataset is provided under `data/sample.csv` for use with `-profile test`. Note: the `test` profile runs the **real** pipeline modules on this data and calls real APIs, so it needs Docker running, the four secrets, and network access — it is not an offline mock.

## Running the pipeline

### Quick test run

```bash
nextflow run main.nf -profile test,docker,emulate_amd64 --outdir results
```

Prerequisites: Docker must be running, and the four secrets — `WP2_BIODIV_API_KEY`, `WP3_OPENAI_API_KEY`, `WP4_OPENAI_API_KEY`, and `WP5_OPENAI_API_KEY` — must be set via `nextflow secrets set`. On Apple Silicon (arm64) the `emulate_amd64` profile is required because the demo images are `amd64`-only; drop it on Intel / Linux x86. The `test` profile points to `data/sample.csv` and `assets/default_mapping.jsonld`, so no `--input` or `--mapping_schema` is needed — but the run is not offline: it executes the real modules against real APIs.

### Custom input run

The `docker` profile runs the real module containers and works end-to-end. On Apple Silicon add `emulate_amd64` (see the quick test run above).

```bash
nextflow run main.nf -profile docker \
    --input path/to/your.csv \
    --outdir results
```

### Custom mapping schema

```bash
nextflow run main.nf -profile docker \
    --input data/my_records.csv \
    --mapping_schema schemas/my_mapping.jsonld \
    --outdir results
```

## Parameters

| Parameter          | Required | Default                         | Description                                                                        |
| ------------------ | -------- | ------------------------------- | ---------------------------------------------------------------------------------- |
| `--input`          | Yes      | —                               | Path to input CSV file containing biodiversity records                             |
| `--mapping_schema` | No       | `assets/default_mapping.jsonld` | Path to RDF mapping schema (JSON-LD or Turtle format)                              |
| `--outdir`         | Yes      | —                               | Directory for pipeline output files                                                |
| `-profile`         | Yes      | —                               | Execution profile: `docker`, `singularity`, `test`, or comma-separated combination |

Parameters can also be supplied via a YAML file:

```bash
nextflow run main.nf -profile docker -params-file params.yaml
```

```yaml
# params.yaml
input: "./data.csv"
mapping_schema: "./assets/default_mapping.jsonld"
outdir: "./results"
```

## Execution profiles

Multiple profiles can be combined: `-profile test,docker`. They load in order, so later profiles override earlier ones.

| Profile       | Description                                                        |
| ------------- | ------------------------------------------------------------------ |
| `test`        | Uses the bundled real sample CSV in `data/`. Runs real modules — needs Docker + the three secrets.      |
| `docker`      | Run module containers with Docker                                  |
| `singularity` | Run module containers with Singularity                             |
| `podman`      | Run module containers with Podman                                  |
| `conda`       | Use Conda environments (not recommended for reproducibility)       |

## Resuming a run

Nextflow caches intermediate results in the `work/` directory. To resume from where a previous run stopped:

```bash
nextflow run main.nf -profile docker --input data.csv --outdir results -resume
```

## Running in the background

```bash
nextflow run main.nf -profile docker --input data.csv --outdir results -bg > pipeline.log 2>&1
```

## Troubleshooting

- **`WARN: Task runtime metrics are not reported when using macOS without a container engine`** — harmless. Nextflow prints this on macOS even when Docker is running; it only means per-task CPU/memory metrics are not collected. Docker is still used and the run is not affected.
