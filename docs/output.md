# BiodivPipeline: Output

All output files are written to the directory specified by `--outdir`. Paths below are relative to that directory.

## Directory structure

```
results/
├── column_standardisation/
│   ├── standardised.csv
│   └── column_mapping.json
├── annotation/
│   ├── annotated.jsonld
│   └── unresolved_terms.csv
├── taxonomy/
│   └── taxonomy_resolved.csv
├── quality/
│   ├── quality_report.json
│   └── flagged_records.csv
├── provisional_concepts/
│   └── provisional_concepts.json
├── rdf/
│   ├── output.ttl
│   ├── output.jsonld
│   └── rdf_report.json
├── reports/
│   └── pipeline_summary.json
└── pipeline_info/
    ├── execution_report_*.html
    ├── execution_timeline_*.html
    ├── execution_trace_*.txt
    ├── pipeline_dag_*.html
    ├── params_*.json
    └── biodivpipeline_software_versions.yml
```

## Output files by module

### Column Standardisation (WP6)

Directory: `column_standardisation/`

| File                  | Format | Description                                                                    |
| --------------------- | ------ | ------------------------------------------------------------------------------ |
| `standardised.csv`    | CSV    | Input data with column headers mapped to ABCD schema terms                     |
| `column_mapping.json` | JSON   | Mapping of original column names to standardised names, with confidence scores |

The standardised CSV is the input for all downstream modules. Original column names like `Sammlerteam` are mapped to ABCD terms like `AgentText`.

### BiodivPortal Annotation (WP2)

Directory: `annotation/`

| File                   | Format  | Description                                                      |
| ---------------------- | ------- | ---------------------------------------------------------------- |
| `annotated.jsonld`     | JSON-LD | Records annotated with ontology concept URIs from BiodivPortal   |
| `unresolved_terms.csv` | CSV     | Terms that could not be matched to any existing ontology concept |

Unresolved terms are passed to the Provisional Concepts module for registration.

### Taxonomy Classification (WP3)

Directory: `taxonomy/`

| File                    | Format | Description                                                                         |
| ----------------------- | ------ | ----------------------------------------------------------------------------------- |
| `taxonomy_resolved.csv` | CSV    | Taxon names resolved to GBIF taxon keys and WFO identifiers, with confidence scores |

### Outlier Detection (WP4)

Directory: `quality/`

| File                  | Format | Description                                                                                       |
| --------------------- | ------ | ------------------------------------------------------------------------------------------------- |
| `quality_report.json` | JSON   | Statistical summary of data quality checks (coordinate ranges, date validity, field completeness) |
| `flagged_records.csv` | CSV    | Records flagged as potential outliers with reason codes                                           |

### Provisional Concepts (WP5)

Directory: `provisional_concepts/`

| File                        | Format | Description                                                                          |
| --------------------------- | ------ | ------------------------------------------------------------------------------------ |
| `provisional_concepts.json` | JSON   | Newly registered provisional concept URIs for terms not found in existing ontologies |

### RDF Transformation (WP7)

Directory: `rdf/`

| File              | Format  | Description                                                        |
| ----------------- | ------- | ------------------------------------------------------------------ |
| `output.ttl`      | Turtle  | RDF triples in Turtle serialisation                                |
| `output.jsonld`   | JSON-LD | RDF triples in JSON-LD serialisation                               |
| `rdf_report.json` | JSON    | Transformation statistics: triple count, unmapped fields, warnings |

These are the primary deliverables — FAIR-compliant RDF representations of the input biodiversity data.

### Report Collection

Directory: `reports/`

| File                    | Format | Description                                                                                       |
| ----------------------- | ------ | ------------------------------------------------------------------------------------------------- |
| `pipeline_summary.json` | JSON   | Aggregated summary of all processing modules: record counts, quality metrics, annotation coverage |

### Pipeline information

Directory: `pipeline_info/`

| File                                   | Description                                                          |
| -------------------------------------- | -------------------------------------------------------------------- |
| `execution_report_*.html`              | Nextflow execution report with resource usage per process            |
| `execution_timeline_*.html`            | Timeline visualisation of process execution                          |
| `execution_trace_*.txt`                | Tab-delimited trace of every task (CPU, memory, duration, exit code) |
| `pipeline_dag_*.html`                  | DAG visualisation of the workflow                                    |
| `params_*.json`                        | Parameters used for this run                                         |
| `biodivpipeline_software_versions.yml` | Versions of all software used in the pipeline                        |
