process OUTLIER_DETECT {
    tag "outlier"
    label 'process_low'

    container 'outlier-detect:latest'
    containerOptions "--network host --env-file ${moduleDir}/.env"

    input:
    path csv

    output:
    path "flagged_records.csv", emit: flagged
    path "versions.yml",        emit: versions

    script:
    """
    export OLLAMA_URL="http://127.0.0.1:11434"
    
    if [ -f "${moduleDir}/.env" ]; then
        echo "Loading local environment from ${moduleDir}/.env"
        # 2. Extract and export the keys dynamically into the container
        export \$(grep -v '^#' "${moduleDir}/.env" | xargs)
    else
        echo "WARNING: No .env file found at ${moduleDir}/.env"
    fi
    
    python /app/app/main_with_cli.py detect-csv --file $csv --output flagged_records.csv --enable-llm

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        python: \$(python --version 2>&1 | sed 's/Python //')
        outlier_detect: "0.1"
    VERSIONS
    """
}