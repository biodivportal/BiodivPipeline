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

Each module publishes its outputs to its own subdirectory. The exact files and schemas are listed in [reference/module-interface.md](../reference/module-interface.md).

## Final pipeline outputs

The three deliverables mandated by Requirement 1 of the Lastenheft:

| # | Output | Location |
| - | ------ | -------- |
| i | Quality-annotated and taxonomically resolved dataset | `final_dataset/final_dataset.csv` |
| ii | RDF triples derived from the expert schema | `rdf/<id>.ttl` + `rdf/validate.json` (skipped by default — see below) |
| iii | Quality reports for each processing step | `reports/pipeline_summary.json`, `reports/pipeline_summary.md` |

### `rdf/` (output ii)

Produced by the WP7/WP8 RDF Matching & Transformation service from a tabular dataset and
an RML mapping. **Skipped by default** (`--skip_rdf true`) because it needs an RML mapping
whose columns match the dataset — a WP8 Schema Editor deliverable — and its image lives in
a registry not everyone can pull. Enable with `--skip_rdf false --mapping_schema <real RML>`;
the service `/validate`s the mapping against the ontology before emitting `<id>.ttl` and a
`validate.json` report.

### `final_dataset/final_dataset.csv`

The annotated records joined with the taxonomy-resolution columns and the per-record
quality columns emitted by the outlier module. Records are joined on the herbarium
accession — the assembler auto-detects the id column (`HerbariumID` / `record_id` / `id`)
and falls back to row-position alignment for modules that emit no id column. The exact
appended column names track whatever the taxonomy and outlier modules currently produce,
so the dataset stays valid as those schemas evolve.

### `reports/pipeline_summary.{json,md}`

An aggregation of every module's output into one report: columns mapped (and flagged for
review), unresolved annotation terms, taxa resolved (with mean confidence), records
flagged by the outlier module grouped by severity, provisional concepts registered, and
RDF validation status. The `.json` is machine-readable; the `.md` is a human-readable overview.

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

Every module reports the versions of the tools it used (a `versions.yml`), and the pipeline
aggregates them into `biodivpipeline_software_versions.yml` **automatically on every run** —
there is no separate command to run. Open that file to see every tool and version in one place.
