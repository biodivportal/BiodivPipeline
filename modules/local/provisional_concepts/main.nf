process PROVISIONAL_CONCEPTS {
    tag "concepts"
    label 'process_single'

    secret 'WP5_LLM_API_KEY'

    //container 'ghcr.io/mitchell7970/wp5-provisional-concepts:demo'
    container 'ghcr.io/dabauer/wp5:latest'
    input:
    path unresolved // resolves the csv :crossed_fingers:
    // Need to add ontologies once the recommender is implemented

    output:
    path "provisional_concepts.json", emit: concepts
    path "provisional_concepts.csv",  emit: csv
    path "versions.yml",              emit: versions

    script:
    // The container ships two resolver paths:
    //   * taxon    (GBIF, no API key)         -> enabled by default (pass --skip-species to disable)
    //   * locality (ENVO embeddings + an LLM) -> enabled by default (pass --skip-localities to disable)
    // Locality resolution needs an OpenAI-compatible key. To enable it:
    //   1. set params.provisional_concepts_skip_localities = false (kept true by default so the pipeline stays green without any secret)
    //   2. the process already declares `secret 'WP5_LLM_API_KEY'`
    //   3. run `nextflow secrets set WP5_LLM_API_KEY <key>`
    def skip_species_flag = params.provisional_concepts_skip_species ? '--skip-species' : ''
    def skip_localities_flag = params.provisional_concepts_skip_localities ? '--skip-localities' : ''

    def id_arg = params.provisional_concepts_id_col ? "--id-col '${params.provisional_concepts_id_col}'" : ''
    def unresolved_arg = params.provisional_concepts_unresolved_terms_col ? "--unresolved-terms-col '${params.provisional_concepts_unresolved_terms_col}'" : ''
    def family_arg = params.provisional_concepts_family_col ? "--family-col '${params.provisional_concepts_family_col}'" : ''
    def genus_arg = params.provisional_concepts_genus_col ? "--genus-col '${params.provisional_concepts_genus_col}'" : ''
    def name_arg = params.provisional_concepts_name_col ? "--name-col '${params.provisional_concepts_name_col}'" : ''
    def fullname_arg = params.provisional_concepts_fullname_col ? "--fullname-col '${params.provisional_concepts_fullname_col}'" : ''
    def country_arg = params.provisional_concepts_country_col ? "--country-col '${params.provisional_concepts_country_col}'" : ''
    def locality_arg = params.provisional_concepts_locality_col ? "--locality-col ${params.provisional_concepts_locality_col}" : ''
    def ontology_config_arg = params.provisional_concepts_ontology_config ? "--ontology-config '${params.provisional_concepts_ontology_config}'" : ''
    def limit_arg = params.provisional_concepts_limit ? "--limit ${params.provisional_concepts_limit}" : ''
    def mapping_arg = params.provisional_concepts_mapping ? "--mapping '${params.provisional_concepts_mapping}'" : ''

    def llm_base  = params.provisional_concepts_llm_base_url ? "export WP5_LLM_BASE_URL='${params.provisional_concepts_llm_base_url}'" : ''
    def llm_model = params.provisional_concepts_llm_model  ? "export LLM_MODEL='${params.provisional_concepts_llm_model}'"  : ''
    """
    ${llm_base}
    ${llm_model}
    python /app/main.py \\
        --input ${unresolved} \\
        --output provisional_concepts.json \\
        ${skip_species_flag} \\
        ${skip_localities_flag} \\
        ${id_arg} \\
        ${unresolved_arg} \\
        ${family_arg} \\
        ${genus_arg} \\
        ${name_arg} \\
        ${fullname_arg} \\
        ${country_arg} \\
        ${locality_arg} \\
        ${ontology_config_arg} \\
        ${limit_arg} \\
        ${mapping_arg}

    python /app/export_csv.py \\
        --input provisional_concepts.json \\
        --output provisional_concepts.csv

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        provisional_concepts: "0.0.1"
        python: \$(python --version | sed 's/Python //')
    VERSIONS
    """
}
