process OUTLIER_DETECT {
    tag "outlier"
    label 'process_low'

    container 'outlier-detect:latest'
    containerOptions '--network host'

    input:
    path csv

    output:
    path "flagged_records.csv", emit: flagged
    path "versions.yml",        emit: versions

    script:
    """
    export OLLAMA_URL="http://127.0.0.1:11434"
    python ${projectDir}/modules/local/outlier_detect/app/main_with_cli.py detect-csv --file $csv --output flagged_records.csv --enable-llm --llm-provider ollama

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        python: \$(python --version 2>&1 | sed 's/Python //')
        outlier_detect: "0.1"
    VERSIONS
    """
}
