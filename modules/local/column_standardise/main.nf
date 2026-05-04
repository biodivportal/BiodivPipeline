process COLUMN_STANDARDISE {
    tag "column_std"
    label 'process_single'

    container 'biodiv/wp6-column-standardise:latest'

    input:
    path csv

    output:
    path "standardised.csv",    emit: csv
    path "column_mapping.json", emit: mapping
    path "versions.yml",        emit: versions

    script:
    """
    # WP6: Map CSV column headers to ABCD schema terms
    # In stub mode, pass through unchanged + generate a mapping file
    cp ${csv} standardised.csv

    cat <<-MAPPING > column_mapping.json
    {
        "HerbariumID": {"abcd_term": "UnitID", "confidence": 0.95},
        "Family": {"abcd_term": "HigherTaxon", "confidence": 0.90},
        "FullNameCache": {"abcd_term": "FullScientificNameString", "confidence": 0.92},
        "Sammlerteam": {"abcd_term": "AgentText", "confidence": 0.85},
        "Sammelnummer": {"abcd_term": "CollectorsFieldNumber", "confidence": 0.88},
        "CollectionDateBegin": {"abcd_term": "ISODateTimeBegin", "confidence": 0.95},
        "Country": {"abcd_term": "Country", "confidence": 0.98},
        "Locality": {"abcd_term": "LocalityText", "confidence": 0.93},
        "Latitude": {"abcd_term": "LatitudeDecimal", "confidence": 0.97},
        "Longitude": {"abcd_term": "LongitudeDecimal", "confidence": 0.97},
        "Genus": {"abcd_term": "GenusOrMonomial", "confidence": 0.94}
    }
    MAPPING

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        column_standardise: 0.1.0
    VERSIONS
    """
}
