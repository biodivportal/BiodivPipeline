process BIODIV_ANNOTATE {
    tag "annotate"
    label 'process_single'

    secret 'WP2_BIODIV_API_KEY' // dedicated WP2 key; aliased to BIODIV_API_KEY in the task script below (matches the WP-prefixed names in docs/usage.md)

    container 'ghcr.io/biodivportal/biodiv-annotate:0.2' // built + published from this module's Dockerfile by .github/workflows/docker-publish.yml

    input:
    path csv

    output:
    path "annotated.jsonld",     emit: annotations
    path "unresolved_terms.csv", emit: unresolved
    path "enriched.csv",         emit: enriched
    path "versions.yml",         emit: versions

    script:
    """
    # WP2 reads BIODIV_API_KEY from the env; alias the dedicated WP2 secret to it so the
    # documented WP-prefixed name works and never collides with other WPs' keys.
    export BIODIV_API_KEY=\$WP2_BIODIV_API_KEY

    python /app/bin/annotate_biodiv.py \\
        --input ${csv} \\
        --out-json annotated.jsonld \\
        --out-unresolved unresolved_terms.csv \\
        --out-enriched-csv enriched.csv \\
        --max-rows ${params.max_rows}

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        annotate_biodiv: "0.1.0"
        python: \$(python --version | sed 's/Python //')
        requests: \$(python -c "import requests; print(requests.__version__)")
    VERSIONS
    """
}
