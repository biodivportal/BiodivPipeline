# BiodivPipeline: Contributing

## Branch model

| Branch                | Purpose                                                     |
| --------------------- | ----------------------------------------------------------- |
| `master`              | Stable releases only. Never commit directly.                |
| `dev`                 | Integration branch. All feature branches merge here via PR. |
| `wp1-*`, `wp2-*`, ... | Feature branches with group name as prefix (multiple per group possible of course)                           |

```
master ← dev ← wp1-fix-docker
                ← wp1-speed-up-conda
                ← wp3-taxonomy-classifier-integration
                ...
```

## Testing

```bash
nextflow run main.nf -profile test,docker --outdir results
```

All modules must show `✔`. See [module-integration-guide.md](module-integration-guide.md) for module-specific implementation instructions.

## Pull request process

1. Create a feature branch from `dev`
2. Make changes and test locally
3. Push and open a PR against `dev`
4. Verify locally (tests are run manually — no CI yet)
5. At least one reviewer approval required
6. Squash-merge or rebase — no merge commits (No worries. Group 1 takes care of merging into dev.)

## Project contacts

- **Coordinator:** Prof. Dr. Adrian Paschke
- **Customer:** Naouel Karam (<karam@infai.org>), Jan Fillies (<fillies@infai.org>)
- **Repository:** [github.com/biodivportal/BiodivPipeline](https://github.com/biodivportal/BiodivPipeline)
