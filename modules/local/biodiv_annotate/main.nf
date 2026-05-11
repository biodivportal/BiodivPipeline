process BIODIV_ANNOTATE {
    tag "annotate"
    label 'process_low'

    container 'biodivpipeline/placeholder:0.1' // TODO: replace with module team's container

    input:
    path csv

    output:
    path "annotated.jsonld",     emit: annotations
    path "unresolved_terms.csv", emit: unresolved
    path "versions.yml",         emit: versions

    script:
    """
    # Stub — module team replaces this script with the real implementation.
    # Emits minimal valid outputs matching the channel contract.

    echo '{"@context": {}, "@graph": []}' > annotated.jsonld
    : > unresolved_terms.csv

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        stub: "0.0.0"
    VERSIONS
    """
}
