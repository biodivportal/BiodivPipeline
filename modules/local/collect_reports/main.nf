process COLLECT_REPORTS {
    tag "reports"
    label 'process_single'

    // Runs on the host with the stdlib-only aggregator in bin/ (no extra deps),
    // mirroring the other host-run modules. Swap in a container here if the
    // pipeline is ever run fully containerised.

    input:
    path column_mapping
    path annotation_unresolved
    path taxonomy_resolved
    path flagged_records
    path provisional_concepts
    path rdf_report

    output:
    path "pipeline_summary.json", emit: summary
    path "pipeline_summary.md",   emit: report
    path "versions.yml",          emit: versions

    script:
    """
    python ${moduleDir}/bin/collect_reports.py \\
        --column-mapping ${column_mapping} \\
        --annotation-unresolved ${annotation_unresolved} \\
        --taxonomy ${taxonomy_resolved} \\
        --flagged ${flagged_records} \\
        --concepts ${provisional_concepts} \\
        --rdf-report ${rdf_report} \\
        --out-json pipeline_summary.json \\
        --out-md pipeline_summary.md

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        collect_reports: "0.1.0"
        python: \$(python --version | sed 's/Python //')
    VERSIONS
    """
}
