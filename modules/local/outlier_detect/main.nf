process OUTLIER_DETECT {
    tag "outlier"
    label 'process_low'

    container 'biodiv/wp4-outlier-detection:latest'

    input:
    path csv

    output:
    path "quality_report.json", emit: report
    path "flagged_records.csv", emit: flagged
    path "versions.yml",        emit: versions

    script:
    """
    # WP4: Outlier & Data-Quality Detection
    # Statistical (IQR, z-score, DBSCAN) + LLM-assisted checks
    # Stub: generate empty quality report

    cat <<-REPORT > quality_report.json
    {
        "total_records": \$(tail -n +2 ${csv} | wc -l),
        "outliers_detected": 0,
        "methods": ["IQR", "z-score", "isolation_forest", "dbscan", "llm"],
        "flags": [],
        "status": "stub"
    }
    REPORT

    # Flagged records: header + severity column
    head -1 ${csv} | sed 's/\$/ ,"outlier_flag","severity_score","explanation"/' > flagged_records.csv

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        outlier_detection: 0.1.0
    VERSIONS
    """
}
