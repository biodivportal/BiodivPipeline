process BIODIV_ANNOTATE {
    tag "annotate"
    label 'process_single'


    input:
    path csv

    output:
    path "annotated.jsonld",     emit: annotations
    path "unresolved_terms.csv", emit: unresolved
    path "versions.yml",         emit: versions

    script:
    """
    export BIODIV_API_KEY="${params.biodiv_api_key}"

    python ${moduleDir}/bin/annotate_biodiv.py \\
        --input ${csv} \\
        --out-json annotated.jsonld \\
        --out-unresolved unresolved_terms.csv \\
        --max-rows ${params.max_rows ?: 30}

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        annotate_biodiv: "0.1.0"
    VERSIONS
    """
}