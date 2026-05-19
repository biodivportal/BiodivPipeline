process BIODIV_ANNOTATE {
    tag "annotate"
    // label 'process_low'
    label 'process_single'

    container 'biodivpipeline/placeholder:0.1' // TODO: replace with module team's container

    input:
    path csv

    output:
    path "annotated.jsonld",     emit: annotations
    path "unresolved_terms.csv", emit: unresolved
    path "versions.yml",         emit: versions

    script:
    """
    : <<'OLD_STUB'
    # Stub — module team replaces this script with the real implementation.
    # Emits minimal valid outputs matching the channel contract.

    echo '{"@context": {}, "@graph": []}' > annotated.jsonld
    : > unresolved_terms.csv

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        stub: "0.0.0"
    VERSIONS
    OLD_STUB
    

    python ${moduleDir}/bin/annotate_biodiv.py \\
        --input ${csv} \\
        --out-json annotated.jsonld \\
        --out-unresolved unresolved_terms.csv \\
        --max-rows 30

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        python: "\$(python --version | sed 's/Python //')"
        biodiv_annotate: "0.1.0"
    VERSIONS
    """
}