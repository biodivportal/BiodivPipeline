# Plant Taxa Resolver

The plant taxa resolver matches unresolved plant names against the GBIF backbone taxonomy.

## Role in the pipeline

This component handles plant taxonomy fields from input records, operating separately from the locality and ENVO resolution path. It evaluates taxonomy headers such as Family, Genus, NameCache, and FullNameCache.

## How it works

1. Taxonomy extraction: Parses source names into rank structures (family, genus, species, and infraspecific ranks). Qualifiers like var., subsp., and f. are detected and mapped to their respective ranks.
2. Rank selection: Selects the lowest infraspecific rank present, defaulting to species rank when no sub-rank exists.
3. GBIF matching: Queries the GBIF backbone API using `pygbif` `species_match`. Match confidence scores map to EXACT (1.0), FUZZY (0.8), HIGHERRANK (0.5), or NONE (0.0).
4. Disposition logic: Assigns REGISTER when no match exists in GBIF, DISCARD for recognized synonyms or reclassifications, or REVIEW when doubt indicators (such as cf., aff., indet., or s.l.) suggest incomplete classification.

## Current status and limits

The plant taxa resolver is functional and integrated into the pipeline. However, development was kept to an initial working implementation to focus resources on the ENVO locality matcher based on client priorities.

Current limitations include lack of hybrid formula parsing and subforma rank handling. Cross-checking candidate plant names against NCBITaxon has not yet been added.

## Configuration

Source logic is located in `resolvers/plant_taxons.py`, with weight thresholds configured in `ontology_config.json`.

## Related documentation

- [Evaluation and performance](../research/evaluation.md): Match confidence metrics and testing notes.
- [Decisions and lessons](../research/decisions.md): Project scoping priorities and trade-offs.
