process TAXONOMY_CLASSIFY {
    secret 'WP3_OPENAI_API_KEY'
    tag "taxonomy"
    label 'process_low'

    container 'ghcr.io/mitchell7970/wp3-taxonomy-classify:demo' // demo image (personal GHCR namespace); TODO(registry): move to ghcr.io/biodivportal/... when org publishing is available

    input:
    path csv

    output:
    path "taxonomy_resolved.csv", emit: resolved
    path "versions.yml",          emit: versions

    script:
    def llm_base_export = params.taxonomy_llm_base_url ? "export OPENAI_BASE_URL='${params.taxonomy_llm_base_url}'" : ''
    """
    ${llm_base_export}
    export OPENAI_API_KEY=\$WP3_OPENAI_API_KEY
    export OPENAI_MODEL='${params.taxonomy_llm_model}'

    taxonomy-classify --input ${csv} --output taxonomy_resolved.csv

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        python: \$(python --version | sed 's/Python //')
        taxonomy_classify: "0.1"
    VERSIONS
    """
}