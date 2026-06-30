process COLUMN_STANDARDISE {
    tag "column_std"
    label 'process_single'

     // container 'biodivpipeline/placeholder:0.1' // TODO: replace with module team's container

    input:
    path csv

    output:
    path "standardised.csv",    emit: csv
    path "column_mapping.json", emit: mapping
    path "versions.yml",        emit: versions

    script:
    """
    # Stub — module team replaces this script with the real implementation.
    # Emits minimal valid outputs matching the channel contract.

    cp ${csv} standardised.csv
    echo '{}' > column_mapping.json

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        stub: "4.2.0"
    VERSIONS
    """
}
