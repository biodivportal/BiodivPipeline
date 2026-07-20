process OUTLIER_DETECT {
    tag "outlier"
    label 'process_low'

    secret 'WP4_OPENAI_API_KEY' // dedicated key; WP4's LLM detector runs in OpenAI mode (kept separate from WP3's key)

    container 'ghcr.io/biodivportal/outlier-detect:0.2'
    containerOptions '--network host'

    input:
    path csv

    output:
    path "flagged_records.csv", emit: flagged
    path "versions.yml",        emit: versions

    script:
    """
    # WP4's LLM detector runs in OpenAI mode (no --use_ollama), so it needs OPENAI_API_KEY.
    # Alias the dedicated WP4 secret so it never collides with WP3's key.
    export OPENAI_API_KEY=\$WP4_OPENAI_API_KEY
    export OPENAI_MODEL='gpt-4o-mini'

    python /app/main_with_cli.py detect-csv --file ${csv} --output flagged_records.csv --enable-llm

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        python: \$(python --version 2>&1 | sed 's/Python //')
        outlier_detect: "0.1"
    VERSIONS
    """
}
