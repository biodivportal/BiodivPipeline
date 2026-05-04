process COLLECT_REPORTS {
    tag "reports"
    label 'process_single'

    input:
    path quality_report
    path rdf_report
    path column_mapping
    path provisional_concepts

    output:
    path "pipeline_summary.json", emit: summary

    script:
    """
    # Collect all per-step reports into a single pipeline summary
    cat <<-SUMMARY > pipeline_summary.json
    {
        "pipeline": "biodivpipeline",
        "version": "0.1.0",
        "reports": {
            "quality": "\$(cat ${quality_report})",
            "rdf": "\$(cat ${rdf_report})",
            "column_mapping": "${column_mapping}",
            "provisional_concepts": "${provisional_concepts}"
        }
    }
    SUMMARY

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        collect_reports: 0.1.0
    VERSIONS
    """
}
