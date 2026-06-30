process PROVISIONAL_CONCEPTS {
    tag "concepts"
    label 'process_single'

    input:
    path unresolved // resolves the csv :crossed_fingers:
    // Need to add ontologies once the recommender is implemented

    output:
    path "provisional_concepts.json", emit: concepts
    path "versions.yml",              emit: versions

    script:
    """
    python ${moduleDir}/bin/main.py \\
        --input ${unresolved} \\
        --output provisional_concepts.json

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        provisional_concepts: "0.0.1"
        python: \$(python --version | sed 's/Python //')
    VERSIONS
    """
}
