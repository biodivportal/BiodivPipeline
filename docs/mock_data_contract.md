# Mock Data Contract for the End-to-End Test

This document defines the mock input data and the expected mock outputs for each local module. The goal is to make the full pipeline executable end-to-end before the real services are available.

## General Rule

The shared identifier across all mock files is:

```text
record_id = HerbariumID
```

The same `record_id` values should appear in all downstream outputs so that the mock pipeline is logically traceable across modules.

## Pipeline Input

### Input file

```text
tests/data/mock/mock_dataset.csv
```

### Important input columns

```text
HerbariumID, Family, FullNameCache, NameCache, Genus, Country, Locality,
Latitude, Longitude, CollectionDateBegin, CollectionDateEnd, Sammlerteam,
Barcode, StableURI
```

The mock dataset contains typical records as well as simple edge cases:

- one normal resolved record,
- one ambiguous taxon name,
- one record with missing coordinates,
- one record with a date range,
- one record with an unresolved locality/concept.

## Module 1: COLUMN_STANDARDISE

### Input

```text
mock_dataset.csv
```

### Outputs

```text
standardised.csv
column_mapping.json
```

### Required fields in `standardised.csv`

```text
record_id, scientific_name, genus, family, country, locality,
decimal_latitude, decimal_longitude, event_date, event_date_end,
collector, barcode, stable_uri
```

## Module 2: BIODIV_ANNOTATE

### Input

```text
standardised.csv
```

### Outputs

```text
annotated.jsonld
unresolved_terms.csv
```

### Purpose of mock output

The mock annotation output simulates matched, partially matched, and unresolved terms. `unresolved_terms.csv` is used by the provisional concept module.

## Module 3: TAXONOMY_CLASSIFY

### Input

```text
standardised.csv
```

### Output

```text
taxonomy_resolved.csv
```

### Required fields

```text
record_id, scientific_name, resolved_name, gbif_key, wfo_id, confidence, status
```

## Module 4: OUTLIER_DETECT

### Input

```text
standardised.csv
```

### Outputs

```text
quality_report.json
flagged_records.csv
```

### Purpose of mock output

The mock output marks simple data-quality issues such as missing coordinates, date ranges, ambiguous taxonomy, and unresolved locality information.

## Module 5: PROVISIONAL_CONCEPTS

### Input

```text
unresolved_terms.csv
```

### Output

```text
provisional_concepts.json
```

### Purpose of mock output

The mock output simulates provisional concepts for unresolved terms that require expert review.

## Module 6: RDF_TRANSFORM

### Inputs

```text
standardised.csv
annotated.jsonld
taxonomy_resolved.csv
mock_schema.jsonld
```

### Outputs

```text
output.ttl
output.jsonld
rdf_report.json
```

### Purpose of mock output

The mock output provides a small deterministic RDF/Turtle and JSON-LD representation of selected records.

## Module 7: COLLECT_REPORTS

### Inputs

```text
quality_report.json
rdf_report.json
column_mapping.json
provisional_concepts.json
```

### Output

```text
pipeline_summary.json
```

### Purpose of mock output

The summary report collects the status and main output paths of all mock modules.

## Expected Result Structure

After a successful mock run, the output directory should contain:

```text
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
    └── biodivpipeline_software_versions.yml
```
