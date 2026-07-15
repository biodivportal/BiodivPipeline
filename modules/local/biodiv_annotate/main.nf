process BIODIV_ANNOTATE {
    tag "annotate"
    label 'process_single'

    secret 'WP2_BIODIV_API_KEY' // BiodivPortal API key; injected into the task env (works for the local executor too)

    input:
    path csv

    output:
    path "annotated.jsonld",     emit: annotations
    path "unresolved_terms.csv", emit: unresolved
    path "enriched.csv",         emit: enriched
    path "versions.yml",         emit: versions

    script:
    """
    # The script reads BIODIV_API_KEY from the env; alias the WP2-scoped secret to it.
    export BIODIV_API_KEY=\$WP2_BIODIV_API_KEY

    python ${moduleDir}/bin/annotate_biodiv.py \\
        --input ${csv} \\
        --out-json annotated.jsonld \\
        --out-unresolved unresolved_terms.csv \\
        --out-enriched-csv enriched.csv \\
        --max-rows ${params.max_rows ?: 30}

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        annotate_biodiv: "0.1.0"
        python: \$(python --version | sed 's/Python //')
        requests: \$(python -c "import requests; print(requests.__version__)")
    VERSIONS
    """
}
