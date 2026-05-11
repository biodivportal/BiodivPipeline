# BiodivPipeline: Usage

## Prerequisites

| Requirement                          | Minimum | Tested          |
| ------------------------------------ | ------- | --------------- |
| Java                                 | 11+     | OpenJDK 21.0.11 |
| [Nextflow](https://www.nextflow.io/) | >= 24.x | 26.04.0         |
| [Docker](https://www.docker.com/)    | >= 20.x | 29.3.0          |

## Input data

The pipeline expects a CSV file with biodiversity specimen records and a header row. Column names do not need to follow any specific standard — the first pipeline module is responsible for mapping headers to a target schema.

A small mock dataset is provided under `test_data/sample.csv` for use with `-profile test`.

## Running the pipeline

### Quick test run

```bash
nextflow run main.nf -profile test,docker --outdir results
```

The `test` profile points to `test_data/sample.csv` and `assets/default_mapping.jsonld` so no other parameters are needed.

### Custom input run

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
| `test`        | Uses the bundled mock CSV in `test_data/`. No other params needed. |
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

Or use `screen` / `tmux` for a detached session.

## Nextflow memory

If Nextflow requests too much JVM memory, set:

```bash
export NXF_OPTS='-Xms1g -Xmx4g'
```
