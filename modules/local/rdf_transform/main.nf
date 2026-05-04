process RDF_TRANSFORM {
    tag "rdf"
    label 'process_low'

    container 'biodiv/wp7-rdf-transform:latest'

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
    # WP7: RDF Matching & Transformation
    # Transform tabular records into RDF triples using expert mapping schema
    # Stub: generate minimal valid Turtle

    cat <<-TTL > output.ttl
    @prefix dwc: <http://rs.tdwg.org/dwc/terms/> .
    @prefix dcterms: <http://purl.org/dc/terms/> .

    # Stub output — real transformation pending WP7 service
    TTL

    cat <<-JSONLD > output.jsonld
    {
        "@context": {
            "dwc": "http://rs.tdwg.org/dwc/terms/",
            "dcterms": "http://purl.org/dc/terms/"
        },
        "@graph": [],
        "status": "stub"
    }
    JSONLD

    cat <<-REPORT > rdf_report.json
    {
        "input_records": \$(tail -n +2 ${csv} | wc -l),
        "triples_generated": 0,
        "mapping_schema": "${mapping_schema}",
        "status": "stub"
    }
    REPORT

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        rdf_transform: 0.1.0
    VERSIONS
    """
}
