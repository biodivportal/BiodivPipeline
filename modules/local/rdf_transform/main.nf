process RDF_TRANSFORM {
    tag "rdf"
    label 'process_low'

    // container 'biodivpipeline/placeholder:0.1' // TODO: replace with module team's container

    input:
    path csv
    path annotations
    path taxonomy
    path mapping_schema

    output:
    path "output.ttl",          emit: rdf_turtle
    path "output.jsonld",       emit: rdf_jsonld
    path "rdf_report.json",     emit: report
    path "versions.yml",        emit: versions

    script:
    """
    # Stub — module team replaces this script with the real implementation.
    # Emits minimal valid outputs matching the channel contract.

    : > output.ttl
    echo '{"@context": {}, "@graph": []}' > output.jsonld
    echo '{}' > rdf_report.json

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        stub: "0.0.0"
    VERSIONS
    """
}
