# Running the pipeline

## Prerequisites

| Requirement | Minimum | Tested |
| ----------- | ------- | ------ |
| Java | 11+ | OpenJDK 21.0.11 |
| [Nextflow](https://www.nextflow.io/) | ≥ 24.x | 26.04.0 |
| [Docker](https://www.docker.com/) | ≥ 20.x | 29.3.0 |

## Secrets

Module API keys are read from Nextflow's [secrets store](https://www.nextflow.io/docs/latest/secrets.html) — never commit them. Set each with `nextflow secrets set <NAME> '<value>'`; list them with `nextflow secrets list`.

| Secret | Module (WP) | Used for | Required? |
| ------ | ----------- | -------- | --------- |
| `WP2_BIODIV_API_KEY` | biodiv_annotate (WP2) | BiodivPortal annotation API | Yes |
| `WP3_OPENAI_API_KEY` | taxonomy_classify (WP3) | LLM taxonomy resolution | Yes |
| `WP4_OPENAI_API_KEY` | outlier_detect (WP4) | LLM-assisted outlier detection | Yes |
| `WP5_LLM_API_KEY` | provisional_concepts (WP5) | ENVO / locality resolution | Only if WP5 runs (else `--skip_provisional_concepts`) |

WP3 and WP4 can share one OpenAI key. If `secrets list` disagrees with a module, the module's `secret` declaration is the source of truth.

## Input

A CSV of biodiversity specimen records with a header row. Column names need no particular
standard — the first module maps them to the target schema. A mock dataset ships at
`data/sample.csv` for use with `-profile test`.

## Run

```bash
# bundled test dataset
nextflow run main.nf -profile test,docker --outdir results

# your own data
nextflow run main.nf -profile docker --input path/to/your.csv --outdir results

# with a real RDF mapping schema (enables RDF output)
nextflow run main.nf -profile docker --input your.csv --mapping_schema your_mapping.ttl --skip_rdf false --outdir results
```

On Apple Silicon add `,emulate_amd64` — the demo images are `linux/amd64`.

## Parameters

| Parameter | Required | Default | Description |
| --------- | -------- | ------- | ----------- |
| `--input` | Yes | — | Input CSV of biodiversity records |
| `--outdir` | Yes | — | Output directory |
| `--mapping_schema` | No | `assets/default_mapping.jsonld` | RML mapping for RDF (Turtle or JSON-LD) |
| `--skip_provisional_concepts` | No | `false` | Skip WP5 (avoids needing its key) |
| `--skip_rdf` | No | `true` | Skip WP7 RDF — needs a matching mapping and a pullable image |
| `-profile` | Yes | — | Comma-separated: `test`, `docker`, `singularity`, `emulate_amd64` |

Parameters can also be supplied from a YAML file with `-params-file params.yaml`.

## Profiles

| Profile | Effect |
| ------- | ------ |
| `test` | Uses the bundled mock CSV; no other params needed |
| `docker` | Run module containers with Docker |
| `singularity` | Run module containers with Singularity |
| `emulate_amd64` | Force `linux/amd64` (needed on Apple Silicon) |

Combine with commas (`-profile test,docker`); later profiles override earlier ones. The
standard nf-core `podman`, `conda`, and `apptainer` profiles are also available.

## Configuration

**Changing configuration never requires rebuilding a container.** The module images are
fixed; *how* they run is controlled by parameters and config files that Nextflow reads
fresh on every run. You only rebuild an image if you change a module's *source code* —
never for a settings change.

Three ways to configure a run, lowest to highest effort:

1. **Command-line parameters** — the common knobs:

   ```bash
   nextflow run main.nf -profile docker --input data.csv --outdir results \
       --max_rows 500 --taxonomy_llm_model gpt-4o --skip_provisional_concepts true
   ```

2. **A parameters file** — the same knobs, version-controlled:

   ```bash
   nextflow run main.nf -profile docker -params-file params.yaml --outdir results
   ```

3. **A custom config (`-c`)** — for per-module compute resources or a module's `ext`
   tunables, without editing the repo:

   ```bash
   nextflow run main.nf -profile docker --input data.csv --outdir results -c my.config
   ```

### Tuning knobs

Beyond the run-shape parameters listed above, each module exposes its settings as params —
so the client can tune behaviour without touching code or images:

| Parameter | Module (WP) | Effect |
| --------- | ----------- | ------ |
| `--max_rows` | biodiv_annotate (WP2) | Rows annotated per run |
| `--taxonomy_llm_model`, `--taxonomy_llm_base_url` | taxonomy_classify (WP3) | LLM model / endpoint (any OpenAI-compatible API) |
| `--provisional_concepts_llm_model`, `--provisional_concepts_llm_base_url` | provisional_concepts (WP5) | WP5 LLM model / endpoint |
| `--provisional_concepts_skip_species`, `--provisional_concepts_skip_localities` | provisional_concepts (WP5) | Toggle WP5's two resolution paths |

The RDF module additionally accepts `output_format`, `delimiter`, and `source_type` via
`ext` in a `-c` config. Every module's inputs and outputs are listed in
[../reference/module-interface.md](../reference/module-interface.md).

## Resume & background

```bash
# reuse cached steps from a previous run
nextflow run main.nf -profile docker --input data.csv --outdir results -resume

# run in the background, logging to a file
nextflow run main.nf -profile docker --input data.csv --outdir results -bg > run.log 2>&1
```
