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
├── final_dataset/
├── reports/
└── pipeline_info/
```

Each module publishes its outputs to its own subdirectory. The file contents and schemas inside those subdirectories are owned by the module teams and are described in each module's interface spec.

## Final pipeline outputs

The three deliverables mandated by Requirement 1 of the Lastenheft:

| # | Output | Location |
| - | ------ | -------- |
| i | Quality-annotated and taxonomically resolved dataset | `final_dataset/final_dataset.csv` |
| ii | RDF triples derived from the expert schema | `rdf/output.ttl`, `rdf/output.jsonld` |
| iii | Quality reports for each processing step | `reports/pipeline_summary.json`, `reports/pipeline_summary.md` |

### `final_dataset/final_dataset.csv`

The annotated records joined with taxonomy resolution (`gbif_key`, `wfo_id`, `confidence`, …) and a per-record quality summary (`quality_issue_count`, `quality_max_severity`, `quality_issues`). Records are joined on the herbarium accession, regardless of whether upstream modules label the id column `HerbariumID` or `record_id`.

### `reports/pipeline_summary.{json,md}`

An aggregation of every module's output into one report: columns mapped, unresolved annotation terms, taxa resolved (with mean confidence), quality flags grouped by severity and issue type, provisional concepts registered, and RDF triple counts. The `.json` is machine-readable; the `.md` is a human-readable overview.

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
