process TAXONOMY_CLASSIFY {
    tag "taxonomy"
    label 'process_low'

    container 'biodivpipeline/placeholder:0.1' // TODO: replace with module team's container

    input:
    path csv

    output:
    path "taxonomy_resolved.csv", emit: resolved
    path "versions.yml",          emit: versions

    script:
    """
    # Stub — module team replaces this script with the real implementation.
    # Emits minimal valid outputs matching the channel contract.

    cp ${csv} taxonomy_resolved.csv

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        stub: "0.0.0"
    VERSIONS
    """
}
