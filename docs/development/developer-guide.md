# Developer guide

How to contribute to and extend the pipeline.

## Branch model

| Branch | Purpose |
| ------ | ------- |
| `master` | Stable releases only. Never commit directly. |
| `dev` | Integration branch. Feature branches merge here via PR. |
| `wp<N>-<short-desc>` | Feature branches, prefixed with the group number |

## Pull requests

1. Branch off `dev`: `git checkout -b wp<N>-<short-desc>`
2. Make changes and test locally — `nextflow run main.nf -profile test,docker --outdir results` (all modules show `✔`)
3. Push and open a PR against `dev`
4. At least one reviewer approves
5. Squash-merge — no merge commits (WP1 handles merging into `dev`)

There is no CI yet, so verify locally before opening a PR.

## Adding or implementing a module

You own one folder; WP1 owns the orchestration.

```
modules/local/<your_module>/
├── main.nf     # Nextflow glue — WP1 writes this with you; don't rewrite from scratch
└── bin/        # your scripts (optional)
```

Don't touch the root `main.nf`, `workflows/`, `nextflow.config`, `conf/`, or `subworkflows/`.

Three ways to implement the logic (all equivalent from the pipeline's point of view):

| Approach | How | When |
| -------- | --- | ---- |
| Embedded script | Shell/Python directly in the `script:` block of `main.nf` | Short logic, no external deps |
| `bin/` script | Put it in `bin/` and call by filename (Nextflow adds `bin/` to PATH) | Cleaner separation |
| Container | Set `container '<registry>/<image>:<tag>'` and call its CLI | Complex deps or a REST service |

Your module's exact input/output contract — filenames must match — is in
[reference/module-interface.md](../reference/module-interface.md).

Every module must emit `versions.yml`:

```bash
cat <<-VERSIONS > versions.yml
"${task.process}":
    my_tool: "$(my_tool --version 2>&1 | head -1)"
VERSIONS
```

## Contacts

- **Coordinator:** Prof. Dr. Adrian Paschke
- **Customer:** Naouel Karam (<karam@infai.org>), Jan Fillies (<fillies@infai.org>)
- **Repository:** [github.com/biodivportal/BiodivPipeline](https://github.com/biodivportal/BiodivPipeline)
