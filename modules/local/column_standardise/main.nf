process COLUMN_STANDARDISE {
    tag "column_std"
    label 'process_single'

    container 'ghcr.io/biodivportal/column-standardise:0.1' // built + published from this module's vendored Dockerfile by .github/workflows/docker-publish.yml

    input:
    path csv

    output:
    path "standardised.csv",    emit: csv
    path "column_mapping.json", emit: mapping
    path "versions.yml",        emit: versions

    script:
    """
    # WP6 ABCD Column Standardizer CLI.
    # Its MappingPipeline resolves data/abcd.json + app/config/profiling_targets.json
    # relative to the working directory, so we cd into the image's /app (where those
    # files live) and write outputs back to the Nextflow task dir via \$OLDPWD.
    work_dir=\$PWD
    cd /app
    python -m app.standardize \\
        --input "\$work_dir/${csv}" \\
        --out-csv "\$work_dir/standardised.csv" \\
        --out-map "\$work_dir/column_mapping.json"

    cd "\$work_dir"

    cat <<-VERSIONS > versions.yml
    "${task.process}":
        column_standardise: \$(cd /app && python -m app.standardize --version | sed 's/.* //')
    VERSIONS
    """
}
