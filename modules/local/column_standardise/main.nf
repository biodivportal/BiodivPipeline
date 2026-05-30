process COLUMN_STANDARDISE {
    tag "column_std"
    label 'process_single'

    container 'biodivpipeline/placeholder:0.1' // TODO: replace with module team's container

    input:
    path csv

    output:
    path "standardised.csv",    emit: csv
    path "column_mapping.json", emit: mapping
    path "versions.yml",        emit: versions

    script:
    """
    # Mock implementation for end-to-end pipeline testing.
    # Emits deterministic, realistic outputs matching the module contract.

    cat > standardised.csv <<'EOF'
record_id,scientific_name,genus,family,country,locality,decimal_latitude,decimal_longitude,event_date,event_date_end,collector,barcode,stable_uri
B100064379,Echium vulgare L.,Echium,BORAGINACEAE,Germany,"Lkr. Bad-Toelz-Wolfratshausen, W Vorderriss",47.5428,11.3556,2001-08-07,,"Willing,R. & Willing,E.",B 10 0064379,https://herbarium.bgbm.org/object/B100064379
B100094552,Hieracium L.,Hieracium,ASTERACEAE,Germany,,,,,,unclear,B 10 0094552,https://herbarium.bgbm.org/object/B100094552
B100132913,Atriplex laciniata L.,Atriplex,CHENOPODIACEAE,Germany,"Niedersachsen, Memmert",53.6386,6.86639,1995-08-21,,Kuhbier M.H.,B 10 0132913,https://herbarium.bgbm.org/object/B100132913
B100198478,Juniperus communis,Juniperus,Cupressaceae,Germany,"Berlin, Karlshorst",52.4739,13.5136,1926-09-01,1926-09-30,R. Gross,B 10 0198478,http://herbarium.bgbm.org/object/B100198478
B100263237,Serratula tinctoria L.,Serratula,COMPOSITAE,Germany,"Potsdam in sicris",,,1882-07,,Bornmueller J.F.N.,B 10 0263237,https://herbarium.bgbm.org/object/B100263237
EOF

    cat > column_mapping.json <<'EOF'
{
  "HerbariumID": "record_id",
  "FullNameCache": "scientific_name",
  "Genus": "genus",
  "Family": "family",
  "Country": "country",
  "Locality": "locality",
  "Latitude": "decimal_latitude",
  "Longitude": "decimal_longitude",
  "CollectionDateBegin": "event_date",
  "CollectionDateEnd": "event_date_end",
  "Sammlerteam": "collector",
  "Barcode": "barcode",
  "StableURI": "stable_uri"
}
EOF

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        stub: "0.1.0"
    VERSIONS
    """
}
