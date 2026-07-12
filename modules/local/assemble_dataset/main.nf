process ASSEMBLE_DATASET {
    tag "assemble"
    label 'process_single'

    // Runs on the host with the stdlib-only assembler in bin/ (no extra deps),
    // mirroring the other host-run modules. Swap in a container here if the
    // pipeline is ever run fully containerised.

    input:
    path base        // annotated records (base table, e.g. enriched.csv)
    path taxonomy    // taxonomy resolution CSV
    path flagged     // quality flags CSV

    output:
    path "final_dataset.csv", emit: dataset
    path "versions.yml",      emit: versions

    script:
    """
    python ${moduleDir}/bin/assemble_dataset.py \\
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
