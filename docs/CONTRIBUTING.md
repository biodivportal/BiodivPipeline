# BiodivPipeline: Contributing

## Branch model

| Branch | Purpose |
|---|---|
| `master` | Stable releases only. Never commit directly. |
| `dev` | Integration branch. All feature branches merge here via PR. |
| `wp1-*`, `wp2-*`, ... | Feature branches per work package |

```
master ← dev ← wp1-nf-core-pipeline
                ← wp2-annotator-service
                ← wp3-taxonomy-classifier
                ...
```

## Git conventions

### Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `build`

Examples:
```
feat(pipeline): wire 7 modules into biodivpipeline workflow DAG
docs: rewrite README for biodiversity pipeline
fix(schema): remove samplesheet validation from nextflow_schema.json
chore: clean .gitignore and remove stray Nextflow artifacts
```

### Branch naming

```
wp<N>-<short-description>
```

Examples: `wp1-nf-core-pipeline`, `wp2-annotator-service`, `wp4-outlier-detection`

## Adding a new module

Each module lives in `modules/local/<module_name>/main.nf`. Follow this interface:

### Module structure

```groovy
process MODULE_NAME {
    tag "$input_file"
    label 'process_single'

    input:
    path input_file

    output:
    path "output_file.ext", emit: output_name
    path "versions.yml",    emit: versions

    script:
    """
    # Your processing logic here

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        tool_name: \$(tool --version)
    END_VERSIONS
    """
}
```

### Wiring into the workflow

1. Add the module import to `workflows/biodivpipeline.nf`
2. Call the process and connect its inputs/outputs to the DAG
3. Mix versions into `ch_versions`: `ch_versions = ch_versions.mix(MODULE_NAME.out.versions)`
4. Add a `publishDir` entry in `conf/modules.config`

### Publishing config

In `conf/modules.config`:

```groovy
withName: MODULE_NAME {
    publishDir = [
        path: { "${params.outdir}/directory_name" },
        mode: params.publish_dir_mode,
        saveAs: { filename -> filename.equals('versions.yml') ? null : filename }
    ]
}
```

## Testing

Run the pipeline with the test profile to verify changes:

```bash
nextflow run main.nf -profile test,docker --outdir results
```

The test profile uses `test_data/sample.csv` (109 records) and `assets/default_mapping.jsonld`.

All 7 modules should complete successfully:

```
NFCORE_BIODIVPIPELINE:BIODIVPIPELINE:COLUMN_STANDARDISE
NFCORE_BIODIVPIPELINE:BIODIVPIPELINE:BIODIV_ANNOTATE
NFCORE_BIODIVPIPELINE:BIODIVPIPELINE:TAXONOMY_CLASSIFY
NFCORE_BIODIVPIPELINE:BIODIVPIPELINE:OUTLIER_DETECT
NFCORE_BIODIVPIPELINE:BIODIVPIPELINE:PROVISIONAL_CONCEPTS
NFCORE_BIODIVPIPELINE:BIODIVPIPELINE:RDF_TRANSFORM
NFCORE_BIODIVPIPELINE:BIODIVPIPELINE:COLLECT_REPORTS
```

## Pull request process

1. Create a feature branch from `dev`
2. Make changes and test locally
3. Push and open a PR against `dev`
4. Ensure the pipeline test passes
5. Request review from at least one team member
6. Squash-merge or rebase-merge (no merge commits)

## Project contacts

- **Coordinator:** Prof. Dr. Adrian Paschke
- **Customer:** Naouel Karam (karam@infai.org), Jan Fillies (fillies@infai.org)
- **Repository:** [github.com/biodivportal/BiodivPipeline](https://github.com/biodivportal/BiodivPipeline)
