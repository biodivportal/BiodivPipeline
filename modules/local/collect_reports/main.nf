process COLLECT_REPORTS {
    tag "reports"
    label 'process_single'

    container 'biodivpipeline/placeholder:0.1' // TODO: replace with module team's container

    input:
    path quality_report
    path rdf_report
    path column_mapping
    path provisional_concepts

    output:
    path "pipeline_summary.json", emit: summary

    script:
    """
    # Mock aggregator for end-to-end pipeline testing.
    # Real implementation will merge per-module reports dynamically.

    cat > pipeline_summary.json <<'EOF'
{
  "pipeline_status": "success",
  "records_processed": 5,
  "steps": {
    "column_standardisation": "success",
    "annotation": "success",
    "taxonomy_classification": "success",
    "outlier_detection": "success",
    "provisional_concepts": "success",
    "rdf_transformation": "success"
  },
  "outputs": {
    "standardised_dataset": "column_standardisation/standardised.csv",
    "column_mapping": "column_standardisation/column_mapping.json",
    "annotations": "annotation/annotated.jsonld",
    "unresolved_terms": "annotation/unresolved_terms.csv",
    "taxonomy": "taxonomy/taxonomy_resolved.csv",
    "quality_report": "quality/quality_report.json",
    "flagged_records": "quality/flagged_records.csv",
    "provisional_concepts": "provisional_concepts/provisional_concepts.json",
    "rdf_turtle": "rdf/output.ttl",
    "rdf_jsonld": "rdf/output.jsonld",
    "rdf_report": "rdf/rdf_report.json"
  }
}
EOF
    """
}
