# Module Integration Guide

This is the one-stop reference for WP2–WP7 teams implementing their module in the BiodivPipeline.

You do not need to understand Nextflow to contribute. You own one folder. You write one script (or build one container). WP1 handles the rest.

---

## What you own

```
modules/local/<your_module>/
├── main.nf        ← Nextflow glue (WP1 writes this with you — do not rewrite from scratch)
└── bin/           ← your scripts live here (optional, see below)
    └── your_script.py
```

You never touch:

- `main.nf` at the repo root
- `workflows/biodivpipeline.nf`
- `nextflow.config`, `conf/`, `subworkflows/`

---

## Three ways to implement your module

| Approach             | How                                                                   | When to use                                              |
| -------------------- | --------------------------------------------------------------------- | -------------------------------------------------------- |
| **Embedded script**  | Write shell/Python directly in the `script:` block of `main.nf`       | Short, self-contained logic with no external deps        |
| **`bin/` script**    | Put your script in `modules/local/<module>/bin/`, call it by name     | Cleaner separation; Nextflow auto-adds `bin/` to PATH    |
| **Docker container** | Set `container 'ghcr.io/biodivportal/your-tool:1.0'` and call its CLI | Complex dependencies, external services, production code |

All three produce the same result from the pipeline's perspective.

---

## The `bin/` pattern (recommended for scripts)

```
modules/local/biodiv_annotate/
├── main.nf
└── bin/
    └── annotate.py   ← Nextflow auto-adds this dir to PATH
```

```groovy
// in main.nf script block:
script:
"""
annotate.py --input $csv --output-dir .
"""
```

No import, no path — just call the script by filename.

---

## Module contracts

Each module has a fixed input/output contract. Your script must read the input files and produce exactly the output files listed. The filenames must match.

### COLUMN_STANDARDISE — `modules/local/column_standardise/`

> Maps raw CSV column headers to target schema terms.

| Direction | File                  | Format                              |
| --------- | --------------------- | ----------------------------------- |
| Input     | `<any>.csv`           | Raw biodiversity records CSV        |
| Output    | `standardised.csv`    | Same records, headers remapped      |
| Output    | `column_mapping.json` | Original → standardised header map  |
| Output    | `versions.yml`        | Tool version declaration (required) |

---

### BIODIV_ANNOTATE — `modules/local/biodiv_annotate/`

> Annotates records against biodiversity ontologies.

| Direction | File                   | Format                              |
| --------- | ---------------------- | ----------------------------------- |
| Input     | `standardised.csv`     | Output of COLUMN_STANDARDISE        |
| Output    | `annotated.jsonld`     | Records with ontology term URIs     |
| Output    | `unresolved_terms.csv` | Terms that could not be matched     |
| Output    | `versions.yml`         | Tool version declaration (required) |

---

### TAXONOMY_CLASSIFY — `modules/local/taxonomy_classify/`

> Resolves taxon names to GBIF/WFO identifiers.

| Direction | File                    | Format                              |
| --------- | ----------------------- | ----------------------------------- |
| Input     | `standardised.csv`      | Output of COLUMN_STANDARDISE        |
| Output    | `taxonomy_resolved.csv` | Records with resolved taxon IDs     |
| Output    | `versions.yml`          | Tool version declaration (required) |

---

### OUTLIER_DETECT — `modules/local/outlier_detect/`

> Flags records with bad coordinates, dates, or semantic anomalies.

| Direction | File                  | Format                              |
| --------- | --------------------- | ----------------------------------- |
| Input     | `standardised.csv`    | Output of COLUMN_STANDARDISE        |
| Output    | `quality_report.json` | Quality check summary               |
| Output    | `flagged_records.csv` | Records flagged with reason codes   |
| Output    | `versions.yml`        | Tool version declaration (required) |

---

### PROVISIONAL_CONCEPTS — `modules/local/provisional_concepts/`

> Registers unresolved terms as provisional concept URIs.

| Direction | File                        | Format                              |
| --------- | --------------------------- | ----------------------------------- |
| Input     | `unresolved_terms.csv`      | Output of BIODIV_ANNOTATE           |
| Output    | `provisional_concepts.json` | Newly registered provisional URIs   |
| Output    | `versions.yml`              | Tool version declaration (required) |

---

### RDF_TRANSFORM — `modules/local/rdf_transform/`

> Converts the cleaned, annotated data into RDF triples.

| Direction | File                    | Format                              |
| --------- | ----------------------- | ----------------------------------- |
| Input     | `standardised.csv`      | Output of COLUMN_STANDARDISE        |
| Input     | `annotated.jsonld`      | Output of BIODIV_ANNOTATE           |
| Input     | `taxonomy_resolved.csv` | Output of TAXONOMY_CLASSIFY         |
| Input     | `<mapping_schema>`      | JSON-LD or Turtle mapping schema    |
| Output    | `output.ttl`            | RDF triples (Turtle)                |
| Output    | `output.jsonld`         | RDF triples (JSON-LD)               |
| Output    | `rdf_report.json`       | Transformation statistics           |
| Output    | `versions.yml`          | Tool version declaration (required) |

---

### COLLECT_REPORTS — `modules/local/collect_reports/`

> Aggregates all per-module reports into a single pipeline summary.

| Direction | File                        | Format                         |
| --------- | --------------------------- | ------------------------------ |
| Input     | `quality_report.json`       | Output of OUTLIER_DETECT       |
| Input     | `rdf_report.json`           | Output of RDF_TRANSFORM        |
| Input     | `column_mapping.json`       | Output of COLUMN_STANDARDISE   |
| Input     | `provisional_concepts.json` | Output of PROVISIONAL_CONCEPTS |
| Output    | `pipeline_summary.json`     | Aggregated pipeline summary    |

---

## The `versions.yml` requirement

Every module must produce a `versions.yml` file. This is how nf-core tracks reproducibility. Format:

```yaml
"NFCORE_BIODIVPIPELINE:BIODIVPIPELINE:YOUR_PROCESS_NAME":
  your_tool: "1.2.3"
```

Shortest valid way to produce it in your script:

```bash
cat <<-VERSIONS > versions.yml
"${task.process}":
    my_tool: "$(my_tool --version 2>&1 | head -1)"
VERSIONS
```

---

## Container naming (if using Docker)

Push your image to the project's GitHub Container Registry:

```
ghcr.io/biodivportal/<your-module-name>:<semver>
```

Example: `ghcr.io/biodivportal/annotator-service:1.0.0`

Then set in your `main.nf`:

```groovy
container 'ghcr.io/biodivportal/annotator-service:1.0.0'
```

---

## Step-by-step: implementing your module

1. Branch off `dev`: `git checkout -b wp<N>-<short-description>`
2. Navigate to your module: `cd modules/local/<your_module>/`
3. Replace the stub `script:` block in `main.nf` with your real logic
   - or add your script to `bin/` and call it from `script:`
   - or set `container` to your image and call its CLI
4. Remove the placeholder container line if not using Docker:
   ```groovy
   // delete this line if using embedded scripts:
   container 'biodivpipeline/placeholder:0.1'
   ```
5. Test locally:
   ```bash
   nextflow run main.nf -profile test --outdir results
   # All 7 modules must show ✔
   ```
6. Push and open a PR against `dev`
7. CI must be green before merge
