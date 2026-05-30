process OUTLIER_DETECT {
    tag "outlier"
    label 'process_low'

    container 'biodivpipeline/placeholder:0.1' // TODO: replace with module team's container

    input:
    path csv

    output:
    path "quality_report.json", emit: report
    path "flagged_records.csv", emit: flagged
    path "versions.yml",        emit: versions

    script:
    """
    # Mock implementation for end-to-end pipeline testing.
    # Simulates data-quality flags for known test records.

    cat > quality_report.json <<'EOF'
{
  "summary": {
    "records_checked": 5,
    "records_with_warnings": 3,
    "records_with_errors": 0
  },
  "issues": [
    {
      "record_id": "B100094552",
      "field": "decimal_latitude",
      "severity": "warning",
      "issue_type": "missing_coordinate",
      "message": "Latitude and longitude are missing."
    },
    {
      "record_id": "B100198478",
      "field": "event_date_end",
      "severity": "warning",
      "issue_type": "date_range",
      "message": "Collection date is available as a date range."
    },
    {
      "record_id": "B100263237",
      "field": "locality",
      "severity": "warning",
      "issue_type": "unresolved_locality",
      "message": "Locality term could not be mapped with high confidence."
    }
  ]
}
EOF

    cat > flagged_records.csv <<'EOF'
record_id,issue_type,severity,field,message
B100094552,missing_coordinate,warning,decimal_latitude,Latitude and longitude are missing
B100198478,date_range,warning,event_date_end,Collection date is available as a date range
B100263237,unresolved_locality,warning,locality,Locality term could not be mapped with high confidence
EOF

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        stub: "0.1.0"
    VERSIONS
    """
}
