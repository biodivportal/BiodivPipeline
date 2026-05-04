# BiodivPipeline Documentation

## Contents

- [Usage](usage.md) — how to run the pipeline, parameters, input format, and execution profiles
- [Output](output.md) — description of every output file produced by the pipeline
- [Contributing](CONTRIBUTING.md) — git conventions, branch model, and how to add or modify modules

## Overview

BiodivPipeline is an nf-core/Nextflow pipeline that transforms raw biodiversity CSV records into FAIR-compliant RDF triples. It orchestrates 7 processing modules:

1. **Column Standardisation** (WP6) — map CSV headers to ABCD schema terms
2. **BiodivPortal Annotator** (WP2) — match values against curated ontologies
3. **Taxonomy Classifier** (WP3) — resolve taxon names to GBIF/WFO identifiers
4. **Outlier Detection** (WP4) — flag bad coordinates, dates, and semantic mismatches
5. **Provisional Concepts** (WP5) — register unresolved terms in BiodivPortal
6. **RDF Transformation** (WP7) — convert cleaned tabular data into RDF triples
7. **Report Collection** — aggregate all quality and processing reports

For the high-level architecture and quick start, see the [main README](../README.md).

## Technical stack

| Component        | Version                       |
| ---------------- | ----------------------------- |
| Nextflow         | >= 24.x (tested with 26.04.0) |
| nf-core template | 4.0.2                         |
| Java             | 11+ (tested with OpenJDK 21)  |
| Docker           | >= 20.x (tested with 29.3.0)  |

## Project links

- **Repository:** [github.com/biodivportal/BiodivPipeline](https://github.com/biodivportal/BiodivPipeline)
- **nf-core framework:** [nf-co.re](https://nf-co.re)
