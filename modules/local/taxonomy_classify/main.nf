process TAXONOMY_CLASSIFY {
    tag "taxonomy"
    label 'process_low'

    container 'biodiv/wp3-taxonomy-classifier:latest'

    input:
    path csv

    output:
    path "taxonomy_resolved.csv", emit: resolved
    path "versions.yml",          emit: versions

    script:
    """
    # WP3: Land Taxonomy Classifier — resolve taxon names to GBIF/WFO IDs
    # Stub: copy input and add placeholder resolved columns

    head -1 ${csv} | sed 's/\$/ ,"gbif_key","wfo_id","taxonomy_confidence"/' > taxonomy_resolved.csv
    tail -n +2 ${csv} | sed 's/\$/ ,"","","0.0"/' >> taxonomy_resolved.csv

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        taxonomy_classifier: 0.1.0
    VERSIONS
    """
}
