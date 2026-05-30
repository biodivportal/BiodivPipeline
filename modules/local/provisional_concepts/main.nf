process PROVISIONAL_CONCEPTS {
    tag "concepts"
    label 'process_single'

    container 'biodivpipeline/placeholder:0.1' // TODO: replace with module team's container

    input:
    path unresolved_csv

    output:
    path "provisional_concepts.json", emit: concepts
    path "versions.yml",              emit: versions

    script:
    """
    # Mock implementation for end-to-end pipeline testing.
    # Simulates provisional concept proposals from unresolved terms.

    cat > provisional_concepts.json <<'EOF'
{
  "provisional_concepts": [
    {
      "record_id": "B100198478",
      "term": "Karlshorst",
      "field": "locality",
      "target_vocabulary": "GFBio",
      "provisional_uri": "https://data.biodivportal.gfbio.org/provisional/Karlshorst",
      "status": "pending_expert_review"
    },
    {
      "record_id": "B100263237",
      "term": "Potsdam in sicris",
      "field": "locality",
      "target_vocabulary": "GFBio",
      "provisional_uri": "https://data.biodivportal.gfbio.org/provisional/Potsdam_in_sicris",
      "status": "pending_expert_review"
    }
  ]
}
EOF

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        stub: "0.1.0"
    VERSIONS
    """
}
