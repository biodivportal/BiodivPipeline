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
    # Mock implementation for end-to-end pipeline testing.
    # Simulates taxonomy resolution with stable identifiers and confidence scores.

    cat > taxonomy_resolved.csv <<'EOF'
record_id,scientific_name,resolved_name,gbif_key,wfo_id,confidence,status
B100064379,Echium vulgare L.,Echium vulgare,2925884,wfo-0000631123,0.98,resolved
B100094552,Hieracium L.,Hieracium,3123456,,0.72,ambiguous
B100132913,Atriplex laciniata L.,Atriplex laciniata,3084521,wfo-0000542211,0.95,resolved
B100198478,Juniperus communis,Juniperus communis,5284510,wfo-0000185287,0.93,resolved
B100263237,Serratula tinctoria L.,Serratula tinctoria,3132635,wfo-0000123456,0.90,resolved
EOF

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        stub: "0.1.0"
    VERSIONS
    """
}
