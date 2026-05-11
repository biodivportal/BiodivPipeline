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
    # Stub — aggregator. Real implementation merges per-module reports into a single summary.
    echo '{}' > pipeline_summary.json
    """
}
