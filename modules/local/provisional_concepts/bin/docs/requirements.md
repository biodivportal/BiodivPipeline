# Requirements Compliance (WP5)

This document tracks the compliance status of WP5 against the original project specifications (Lastenheft). It summarizes completed features, partial implementations, and deferred items.

## Summary of requirements

The original specification for WP5 called for an independently deployable microservice capable of detecting concepts that the main annotator could not resolve, selecting an appropriate target vocabulary (such as ENVO), and proposing missing items as provisional concepts marked pending curation. Requirements also called for containerized deployment, Nextflow integration, REST API endpoints, and strict read-only operation to avoid overwriting existing ontology data.

## Compliance matrix

| Requirement | Status | Implementation details |
|---|---|---|
| Detect unresolved concepts | Complete | Implemented via LLM splitting and ENVO vector search |
| Select target vocabulary (ENVO) | Complete | Matches across the full active ENVO term set using habitat filtering |
| Propose provisional concepts tagged unverified | Complete | Emits REGISTER disposition with automatically generated concept definitions |
| Return concept URI or human explanation | Complete | ACCEPT returns matched ENVO URI; REGISTER and DISCARD include explanatory text |
| Deployable container image | Complete | Packaged as `provisional-concepts:0.4` supporting CPU and GPU builds |
| Integrated Nextflow process | Complete | Integrated via the `PROVISIONAL_CONCEPTS` pipeline process |
| Process unresolved term lists with context | Complete | Ingests `unresolved_terms.csv` with configurable column mapping |
| Read-only safety (no silent modifications) | Complete | Performs read-only evaluation and outputs proposals without modifying external APIs |
| Expose live REST API service | Deferred | Delivered as a CLI application and Nextflow module rather than a live HTTP service |
| Automatic POST registration to portal API | Deferred | Deferred per client request to ensure human curation before concept entry |

## Deferred and out-of-scope items

- Live REST endpoint: Scoped out in favor of batch CLI and Nextflow container execution.
- Automated API posting (`register.py`): The pipeline generates structured registration proposals with definitions, leaving actual database entry to manual curator review.
- Plant taxa ground-truth benchmarking: Plant resolution is functional via GBIF API calls, but formal ground-truth evaluation and NCBITaxon cross-checks were deferred.

## Related documentation

- [Decisions and lessons](research/decisions.md): Architecture rationale and scope adjustments.
- [USAGE guide](../USAGE.md): Running the module standalone or in containers.
