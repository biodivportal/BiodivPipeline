process TAXONOMY_CLASSIFY {
    secret 'OPENAI_API_KEY'
    tag "taxonomy"
    label 'process_low'

    container 'taxonomy-classify:0.1'   // your built image name

    input:
    path csv

    output:
    path "taxonomy_resolved.csv", emit: resolved
    path "versions.yml",          emit: versions

    script:
    """
    python /app/classify.py --input ${csv} --output taxonomy_resolved.csv
    
    cat <<-VERSIONS > versions.yml
    "${task.process}":
        python: \$(python --version | sed 's/Python //')
        taxonomy_classify: "0.1"
    VERSIONS
    """
}