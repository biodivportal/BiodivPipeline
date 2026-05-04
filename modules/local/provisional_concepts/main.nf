process PROVISIONAL_CONCEPTS {
    tag "concepts"
    label 'process_single'

    container 'biodiv/wp5-provisional-concepts:latest'

    input:
    path unresolved_csv

    output:
    path "provisional_concepts.json", emit: concepts
    path "versions.yml",              emit: versions

    script:
    """
    # WP5: Provisional Concept Identification & Registration
    # Detect unresolved terms, register in BiodivPortal as provisional
    # Stub: pass through with empty registrations

    cat <<-CONCEPTS > provisional_concepts.json
    {
        "unresolved_input": "${unresolved_csv}",
        "registered": [],
        "failed": [],
        "status": "stub"
    }
    CONCEPTS

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        provisional_concepts: 0.1.0
    VERSIONS
    """
}
