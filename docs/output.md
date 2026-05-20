# BiodivPipeline: Output

All output files are written to the directory specified by `--outdir`. Paths below are relative to that directory.

## Directory structure

```
results/
├── column_standardisation/
├── annotation/
├── taxonomy/
├── quality/
├── provisional_concepts/
├── rdf/
├── reports/
└── pipeline_info/
```

Each module publishes its outputs to its own subdirectory. The file contents and schemas inside those subdirectories are owned by the module teams and are described in each module's interface spec.

## Pipeline information

Directory: `pipeline_info/`

Standard Nextflow execution artifacts.

| File                                   | Description                                                          |
| -------------------------------------- | -------------------------------------------------------------------- |
| `execution_report_*.html`              | Nextflow execution report with resource usage per process            |
| `execution_timeline_*.html`            | Timeline visualisation of process execution                          |
| `execution_trace_*.txt`                | Tab-delimited trace of every task (CPU, memory, duration, exit code) |
| `pipeline_dag_*.html`                  | DAG visualisation of the workflow                                    |
| `params_*.json`                        | Parameters used for this run                                         |
| `biodivpipeline_software_versions.yml` | Versions of all software used in the pipeline                        |
