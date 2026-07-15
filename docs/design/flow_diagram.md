# BiodivPipeline — Dataflow

A quick view of how data moves through the pipeline. Reflects the wiring in
[`workflows/biodivpipeline.nf`](../../workflows/biodivpipeline.nf).

```mermaid
flowchart TD
    IN[/"Input CSV — BGBM records"/]
    SCH[/"RML mapping schema<br/>(from WP8 Schema Editor)"/]

    %% branches off the raw input
    IN --> WP6["WP6 · COLUMN_STANDARDISE"]
    IN --> WP2["WP2 · BIODIV_ANNOTATE"]
    IN --> WP4["WP4 · OUTLIER_DETECT"]

    %% annotation fan-out
    WP2 -->|enriched.csv| WP3["WP3 · TAXONOMY_CLASSIFY"]
    WP2 -->|unresolved_terms.csv| WP5["WP5 · PROVISIONAL_CONCEPTS<br/><i>skippable</i>"]

    %% RDF branch
    WP6 -->|standardised.csv| WP7["WP7 · RDF_TRANSFORM<br/><i>skippable (--skip_rdf)</i>"]
    SCH --> WP7

    %% assemble unified dataset (output i) — WP1
    WP2 -->|enriched.csv| ASM["ASSEMBLE_DATASET · WP1"]
    WP3 -->|taxonomy_resolved.csv| ASM
    WP4 -->|flagged_records.csv| ASM

    %% collect reports (output iii) — WP1
    WP6 -->|column_mapping.json| COL["COLLECT_REPORTS · WP1"]
    WP2 -->|unresolved_terms.csv| COL
    WP3 -->|taxonomy_resolved.csv| COL
    WP4 -->|flagged_records.csv| COL
    WP5 -->|provisional_concepts.json| COL
    WP7 -->|validate.json| COL

    %% outputs
    ASM --> O1[/"final_dataset.csv<br/><b>output (i)</b>"/]
    WP7 --> O2[/"RDF triples .ttl<br/><b>output (ii)</b>"/]
    COL --> O3[/"pipeline_summary.json / .md<br/><b>output (iii)</b>"/]

```

## How to read it

- The raw CSV fans out to **three independent branches**: WP6 (column standardisation),
  WP2 (annotation), WP4 (outlier detection).
- WP2's `enriched.csv` feeds **WP3 taxonomy**; its `unresolved_terms.csv` feeds
  **WP5 provisional concepts**.
- **Green — WP1 modules:** `ASSEMBLE_DATASET` joins annotation + taxonomy + quality flags
  into the unified **output (i)**; `COLLECT_REPORTS` aggregates every module's signal into
  **output (iii)**.
- **Orange dashed — skippable:** WP5 (needs an LLM key) and WP7 RDF (needs a matching RML
  mapping) → **output (ii)**.

## The three deliverables (Lastenheft Requirement 1)

| # | Output | Produced by |
| - | ------ | ----------- |
| i | `final_dataset/final_dataset.csv` — quality-annotated + taxonomically resolved dataset | `ASSEMBLE_DATASET` |
| ii | `rdf/<id>.ttl` — RDF triples from the expert mapping | `RDF_TRANSFORM` (skippable) |
| iii | `reports/pipeline_summary.{json,md}` — per-step quality reports | `COLLECT_REPORTS` |
