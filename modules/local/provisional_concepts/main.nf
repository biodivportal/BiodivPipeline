process PROVISIONAL_CONCEPTS {
    tag "concepts"
    label 'process_single'

    container 'ghcr.io/mitchell7970/wp5-provisional-concepts:demo'

    input:
    path unresolved // resolves the csv :crossed_fingers:
    // Need to add ontologies once the recommender is implemented

    output:
    path "provisional_concepts.json", emit: concepts
    path "versions.yml",              emit: versions

    script:
    // The container ships two resolver paths:
    //   * taxon    (GBIF, no API key)         -> --species     (default)
    //   * locality (ENVO embeddings + an LLM) -> --localities
    // Locality resolution needs an OpenAI-compatible key. To enable it:
    //   1. set params.provisional_concepts_localities = true
    //   2. add `secret 'LLM_API_KEY'` to this process
    //   3. run `nextflow secrets set LLM_API_KEY <key>`
    // (kept off by default so the pipeline stays green without any secret).
    def mode_args = params.provisional_concepts_localities ? '--species --localities' : '--species'
    def llm_base  = params.provisional_concepts_llm_base_url ? "export LLM_BASE_URL='${params.provisional_concepts_llm_base_url}'" : ''
    def llm_model = params.provisional_concepts_llm_model  ? "export LLM_MODEL='${params.provisional_concepts_llm_model}'"  : ''
    """
    ${llm_base}
    ${llm_model}
    python /app/main.py \\
        --input ${unresolved} \\
        --output provisional_concepts.json \\
        ${mode_args}

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        provisional_concepts: "0.0.1"
        python: \$(python --version | sed 's/Python //')
    VERSIONS
    """
}
