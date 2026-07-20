process ASSEMBLE_DATASET {
    tag "assemble"
    label 'process_single'

    container 'ghcr.io/biodivportal/assemble-dataset:0.1' // stdlib-only assembler baked into a slim image; built + published by .github/workflows/docker-publish.yml

    input:
    path base        // annotated records (base table, e.g. enriched.csv)
    path taxonomy    // taxonomy resolution CSV
    path flagged     // quality flags CSV

    output:
    path "final_dataset.csv", emit: dataset
    path "versions.yml",      emit: versions

    script:
    """
    python /app/bin/assemble_dataset.py \\
        --base ${base} \\
        --taxonomy ${taxonomy} \\
        --flagged ${flagged} \\
        --out final_dataset.csv

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        assemble_dataset: "0.1.0"
        python: \$(python --version | sed 's/Python //')
    VERSIONS
    """
}
