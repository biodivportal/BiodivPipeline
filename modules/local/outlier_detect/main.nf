process OUTLIER_DETECT {
    tag "outlier"
    label 'process_low'

    container 'outlier-detect:latest'

    input:
    path csv

    output:
    path "quality_report.json", emit: report
    path "flagged_records.csv", emit: flagged
    path "versions.yml",        emit: versions

    script:
    """
    # Stub — module team replaces this script with the real implementation.
    # Emits minimal valid outputs matching the channel contract.

    echo '{}' > quality_report.json
    : > flagged_records.csv

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        stub: "0.0.0"
    VERSIONS
    """
}
