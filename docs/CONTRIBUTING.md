# BiodivPipeline: Contributing

## Branch model

| Branch                | Purpose                                                     |
| --------------------- | ----------------------------------------------------------- |
| `master`              | Stable releases only. Never commit directly.                |
| `dev`                 | Integration branch. All feature branches merge here via PR. |
| `wp1-*`, `wp2-*`, ... | Feature branches per work package                           |

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

## Testing

```bash
nextflow run main.nf -profile test --outdir results
```

All 7 modules must show `✔`. See [docs/module-workflow.md](module-workflow.md) for module-specific implementation instructions.

## Pull request process

1. Create a feature branch from `dev`
2. Make changes and test locally
3. Push and open a PR against `dev`
4. CI must pass before merge
5. At least one reviewer approval required
6. Squash-merge or rebase — no merge commits

## Project contacts

- **Coordinator:** Prof. Dr. Adrian Paschke
- **Customer:** Naouel Karam (karam@infai.org), Jan Fillies (fillies@infai.org)
- **Repository:** [github.com/biodivportal/BiodivPipeline](https://github.com/biodivportal/BiodivPipeline)
