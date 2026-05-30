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
    # Mock implementation for end-to-end pipeline testing.
    # Simulates matched, partially matched, and unresolved annotations.

    cat > annotated.jsonld <<'EOF'
{
  "@context": {
    "dwc": "http://rs.tdwg.org/dwc/terms/",
    "ex": "https://example.org/biodivpipeline/"
  },
  "@graph": [
    {
      "@id": "ex:record/B100064379",
      "dwc:scientificName": "Echium vulgare L.",
      "dwc:country": "Germany",
      "ex:annotationStatus": "matched"
    },
    {
      "@id": "ex:record/B100094552",
      "dwc:scientificName": "Hieracium L.",
      "dwc:country": "Germany",
      "ex:annotationStatus": "partially_matched"
    },
    {
      "@id": "ex:record/B100198478",
      "dwc:locality": "Berlin, Karlshorst",
      "ex:annotationStatus": "unresolved_locality"
    }
  ]
}
EOF

    cat > unresolved_terms.csv <<'EOF'
record_id,field,term,reason
B100094552,scientific_name,Hieracium L.,ambiguous taxon name
B100198478,locality,Karlshorst,locality not mapped to controlled vocabulary
B100263237,locality,Potsdam in sicris,locality spelling not resolved
EOF

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        stub: "0.1.0"
    VERSIONS
    """
}
