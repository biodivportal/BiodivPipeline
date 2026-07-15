# BiodivPipeline

A modular nf-core / Nextflow pipeline scaffold that orchestrates pluggable modules to transform biodiversity CSV records into FAIR-compliant RDF outputs.

**Framework:** [nf-core](https://nf-co.re) template v4.0.2

## Quick start

**Prerequisites:** Java 11+, [Nextflow](https://www.nextflow.io/) >= 24.x, [Docker](https://www.docker.com/) (optional)

```bash
# Run with the bundled mock dataset
nextflow run main.nf -profile test --outdir results

# Run with your own input (TODO: This profile does not work yet with the unfinished modules; more precise: with the placeholder docker dependencies)
nextflow run main.nf -profile docker \
    --input path/to/biodiv.csv \
    --outdir results
```

### Parameters

| Parameter          | Required | Description                                                                                 |
| ------------------ | -------- | ------------------------------------------------------------------------------------------- |
| `--input`          | Yes      | Path to input CSV file (biodiversity records)                                               |
| `--mapping_schema` | No       | Path to RDF mapping schema (JSON-LD or Turtle). Defaults to `assets/default_mapping.jsonld` |
| `--outdir`         | Yes      | Path to output directory                                                                    |
| `-profile`         | Yes      | Execution profile: `docker`, `singularity`, `test`                                          |

## Output

Results are published under `--outdir`. See [docs/output.md](docs/output.md) for the directory layout.

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
└── docs/                        # Documentation
```

## Documentation

- [Usage](docs/usage.md) — how to run, parameters, profiles
- [Output](docs/output.md) — output directory reference
- [Contributing](docs/CONTRIBUTING.md) — git conventions, branch model, module structure
- [Linting](docs/linting_guidelines.md) — Explainer on our linting configuration
- [Resource Monitoring](docs/resource_monitoring.md) - Decision Record regarding automatic monitoring of resources used by the pipeline
- [Testing Guidelines](docs/test_guidelines.md) - Which tests should contributors provide for their components?

Built on the [nf-core](https://nf-co.re) framework — see [`CITATIONS.md`](CITATIONS.md).
