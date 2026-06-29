process PROVISIONAL_CONCEPTS {
    tag "concepts"
    label 'process_single'

    // container 'biodivpipeline/placeholder:0.1' // TODO: replace with module team's container

    input:
    path unresolved_csv

    output:
    path "provisional_concepts.json", emit: concepts
    path "versions.yml",              emit: versions

    script:
    """
    # Stub — module team replaces this script with the real implementation.
    # Emits minimal valid outputs matching the channel contract.

    echo '{}' > provisional_concepts.json

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        stub: "0.0.0"
    VERSIONS
    """
}
