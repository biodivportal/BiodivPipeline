process BIODIV_ANNOTATE {
    tag "annotate"
    label 'process_low'

    container 'biodiv/wp2-annotator:latest'

    input:
    path csv

    output:
    path "annotated.jsonld",     emit: annotations
    path "unresolved_terms.csv", emit: unresolved
    path "versions.yml",         emit: versions

    script:
    """
    # WP2: Wrap BiodivPortal Annotator REST API
    # Batch-submit records, parse JSON-LD, emit annotated + unresolved terms
    # Stub: generate minimal output structure

    cat <<-JSONLD > annotated.jsonld
    {
        "@context": "https://biodivportal.gfbio.org/context.jsonld",
        "total_records": \$(wc -l < ${csv}),
        "annotated": [],
        "status": "stub"
    }
    JSONLD

    # Extract terms that couldn't be resolved (stub: empty)
    echo "term,field,record_id" > unresolved_terms.csv

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        biodiv_annotator: 0.1.0
    VERSIONS
    """
}
