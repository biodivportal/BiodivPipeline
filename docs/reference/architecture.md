# Architecture

BiodivPipeline orchestrates one module per work package (WP). A raw CSV of biodiversity
records is cleaned, annotated, taxonomically resolved, and quality-checked, then assembled
into a unified dataset and summarised. WP1 owns the orchestration and the final assembly.

## Dataflow

Reflects the wiring in [`workflows/biodivpipeline.nf`](../../workflows/biodivpipeline.nf).

```mermaid
flowchart TD
    IN[/"Input CSV — BGBM records"/]
    SCH[/"RML mapping schema<br/>(from WP8 Schema Editor)"/]

    IN --> WP6["WP6 · COLUMN_STANDARDISE"]
    IN --> WP3["WP3 · TAXONOMY_CLASSIFY"]
    IN --> WP4["WP4 · OUTLIER_DETECT"]

    WP3 -->|"taxonomy_resolved.csv: whole dataset + taxonomy"| WP2["WP2 · BIODIV_ANNOTATE"]
    WP2 -->|unresolved_terms.csv| WP5["WP5 · PROVISIONAL_CONCEPTS"]

    WP6 -->|standardised.csv| WP7["WP7 · RDF_TRANSFORM"]
    SCH --> WP7

    WP2 -->|enriched.csv| ASM["ASSEMBLE_DATASET"]
    WP3 -->|taxonomy_resolved.csv (vestigial — already in enriched)| ASM
    WP4 -->|flagged_records.csv| ASM

    WP6 -->|column_mapping.json| COL["COLLECT_REPORTS"]
    WP2 -->|unresolved_terms.csv| COL
    WP3 -->|taxonomy_resolved.csv| COL
    WP4 -->|flagged_records.csv| COL
    WP5 -->|provisional_concepts.json| COL
    WP7 -->|validate.json| COL

    ASM --> O1[/"final_dataset.csv — output (i)"/]
    WP7 --> O2[/"RDF triples .ttl — output (ii)"/]
    COL --> O3[/"pipeline_summary.json / .md — output (iii)"/]

    classDef wp1 fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px;
    classDef skip fill:#fff3e0,stroke:#ef6c00,stroke-dasharray:4 3;
    classDef out fill:#e1f5fe,stroke:#0277bd;
    class ASM,COL wp1;
    class WP5,WP7 skip;
    class O1,O2,O3 out;
```

- The raw CSV fans out to three independent branches: **WP6** (column standardisation),
  **WP3** (taxonomy), **WP4** (outlier detection).
- **WP3** runs on the raw input and returns the whole dataset with the taxonomy/land-cover
  columns appended; that `taxonomy_resolved.csv` feeds **WP2 annotation**, whose `unresolved_terms.csv`
  feeds **WP5**. (The taxonomy join at `ASSEMBLE_DATASET` is now vestigial — the taxonomy
  columns already ride through WP2 into `enriched.csv` — but kept for robustness.)
- **Green (WP1):** `ASSEMBLE_DATASET` builds the unified dataset; `COLLECT_REPORTS`
  aggregates every module's signal.
- **Orange dashed (skippable):** WP5 (needs an LLM key) and WP7 RDF (needs a matching RML
  mapping; enable it from a params-file, not the CLI).

## Modules

| WP | Module | Does |
| -- | ------ | ---- |
| WP6 | COLUMN_STANDARDISE | Map raw headers to ABCD schema terms |
| WP2 | BIODIV_ANNOTATE | Annotate records against biodiversity ontologies |
| WP3 | TAXONOMY_CLASSIFY | Resolve taxa (GBIF) and classify land cover (CLC) |
| WP4 | OUTLIER_DETECT | Flag coordinate, date, and semantic outliers |
| WP5 | PROVISIONAL_CONCEPTS | Register unresolved terms as provisional concepts *(skippable)* |
| WP7 | RDF_TRANSFORM | Transform data + RML mapping into RDF triples *(skippable)* |
| WP1 | ASSEMBLE_DATASET | Join annotation + taxonomy + quality into the final dataset |
| WP1 | COLLECT_REPORTS | Aggregate every module's output into one report |

Exact inputs and outputs per module: [module-interface.md](module-interface.md).

## The three deliverables (Lastenheft Requirement 1)

| # | Output | Produced by |
| - | ------ | ----------- |
| i | `final_dataset/final_dataset.csv` — quality-annotated + taxonomically resolved dataset | ASSEMBLE_DATASET |
| ii | `rdf/transformed.ttl` — RDF triples from the expert mapping | RDF_TRANSFORM *(skippable)* |
| iii | `reports/pipeline_summary.{json,md}` — per-step quality reports | COLLECT_REPORTS |
