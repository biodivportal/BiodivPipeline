# BiodivPipeline

A modular nf-core / Nextflow pipeline scaffold that orchestrates pluggable modules to transform biodiversity CSV records into FAIR-compliant RDF outputs.

**Framework:** [nf-core](https://nf-co.re) template v4.0.2

## Quick start

**Prerequisites:** Java 11+, [Nextflow](https://www.nextflow.io/) ≥ 24.x, and [Docker](https://www.docker.com/) running.

**1. Set the API keys** the modules need (stored in Nextflow's secret vault — see [Required secrets](#required-secrets) for what each does):

```bash
nextflow secrets set WP2_BIODIV_API_KEY '<BiodivPortal key>'
nextflow secrets set WP3_OPENAI_API_KEY '<OpenAI key>'
nextflow secrets set WP4_OPENAI_API_KEY '<OpenAI key>'   # may reuse the WP3 key
nextflow secrets set WP5_LLM_API_KEY '<OpenAI-compatible key>'   # WP5 — or skip WP5 (see below)
```

**2. Run the bundled test dataset:**

```bash
nextflow run main.nf -profile test,docker --outdir results
```

On **Apple Silicon (M-series)** the demo images are `linux/amd64`, so add the emulation profile:

```bash
nextflow run main.nf -profile test,docker,emulate_amd64 --outdir results
```

**3. Run your own data:**

```bash
nextflow run main.nf -profile docker --input path/to/biodiv.csv --outdir results
```

No WP5 key handy? Skip that module and run everything else:

```bash
nextflow run main.nf -profile test,docker --skip_provisional_concepts --outdir results
```

### Required secrets

API keys are read from Nextflow's [secrets store](https://www.nextflow.io/docs/latest/secrets.html) (never committed to git). Set each with `nextflow secrets set <NAME> '<value>'` and list them with `nextflow secrets list`.

| Secret | Module (WP) | Purpose | Required? |
| ------ | ----------- | ------- | --------- |
| `WP2_BIODIV_API_KEY` | `biodiv_annotate` (WP2) | BiodivPortal annotation API | Yes |
| `WP3_OPENAI_API_KEY` | `taxonomy_classify` (WP3) | LLM taxonomy resolution (gpt-4o-mini) | Yes |
| `WP4_OPENAI_API_KEY` | `outlier_detect` (WP4) | LLM-assisted outlier detection | Yes |
| `WP5_LLM_API_KEY` | `provisional_concepts` (WP5) | ENVO / locality concept resolution | Only when WP5 runs — omit with `--skip_provisional_concepts` |

`WP3_OPENAI_API_KEY` and `WP4_OPENAI_API_KEY` can hold the same OpenAI key; `WP2_BIODIV_API_KEY` is a BiodivPortal key. If `nextflow secrets list` disagrees with a module, the module's `secret` declaration is the source of truth.

### Parameters

| Parameter                     | Required | Description                                                                                 |
| ----------------------------- | -------- | ------------------------------------------------------------------------------------------- |
| `--input`                     | Yes      | Path to input CSV file (biodiversity records)                                               |
| `--outdir`                    | Yes      | Path to output directory                                                                     |
| `--mapping_schema`            | No       | Path to RDF mapping schema (JSON-LD or Turtle). Defaults to `assets/default_mapping.jsonld` |
| `--skip_provisional_concepts` | No       | Skip the WP5 provisional-concepts module (avoids needing its key)                           |
| `-profile`                    | Yes      | Execution profile(s): `test`, `docker`, `singularity`, `emulate_amd64` (comma-separated)    |

## Output

Results are published under `--outdir`. See [docs/usage/output.md](docs/usage/output.md) for the directory layout.

## Project structure

```
BiodivPipeline/
├── main.nf                      # Pipeline entry point
├── workflows/biodivpipeline.nf  # Workflow DAG
├── modules/local/               # Pipeline modules (one per work package)
├── conf/                        # Nextflow config profiles
├── assets/                      # Static files (e. g. default mapping schema)
├── data/                        # Input datasets (raw + test sample)
├── subworkflows/                # nf-core shared utilities
└── docs/                        # Documentation (usage / development / design)
```

## Documentation

Docs live under `docs/`, grouped by audience:

**Usage** — running the pipeline

- [Usage](docs/usage/usage.md) — how to run, parameters, profiles
- [Output](docs/usage/output.md) — output directory reference

**Development** — contributing and authoring modules

- [Contributing](docs/development/CONTRIBUTING.md) — git conventions, branch model
- [Module integration guide](docs/development/module-integration-guide.md) — implement your module
- [Linting](docs/development/linting_guidelines.md) — lint configuration decisions
- [Testing guidelines](docs/development/test_guidelines.md) — tests each service must provide

**Design** — decisions and plans

- [Resource monitoring](docs/design/resource_monitoring.md) — runtime/resource metrics decision record
- [WP1 hardening plan (RFC)](docs/design/DRAFT-wp1-hardening-plan.md) — proposed follow-up work

Built on the [nf-core](https://nf-co.re) framework — see [`CITATIONS.md`](CITATIONS.md).
