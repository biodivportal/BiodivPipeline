# BiodivPipeline — Lint Configuration Decisions

## Context

nf-core lint is designed for production pipelines with nf-core's GitHub Actions test/lint CI, AWS test runs, and nf-core registry releases. We don't run that nf-core CI (our only workflow is `docker-publish.yml`, which builds and pushes the module images) and we don't publish to the nf-core registry, so most of these tests don't apply.

## Disabled Rules

| Rule | Reason |
|------|--------|
| `actions_awsfulltest` | No AWS infrastructure (no cloud) |
| `actions_awstest` | No AWS infrastructure |
| `actions_nf_test` | Not using CI for now |
| `actions_schema_validation` | Not using CI for now |
| `files_unchanged` | Template files are intentionally customised for this project |
| `files_exist` (partial) | Only the template files this project doesn't ship are exempted — 6 nf-core workflow files plus assorted template assets (see the note below); every other required file is still enforced |
| `pipeline_todos` | TODOs are intentional during development — re-enable before final submission |
| `multiqc_config` | Pipeline doesn't use MultiQC; custom per-step quality reports used instead |
| `rocrate_readme_sync` | Not publishing to nf-core registry |
| `modules_json` | All modules are written locally (`modules/local/`), none imported from nf-core registry |
| `readme` | The README is intentionally customised for this project, so nf-core's badge/content checks don't apply |

## Note on `files_exist`

`files_exist` is not disabled wholesale — `.nf-core.yml` exempts only the specific paths this
project doesn't ship. They fall into two groups:

- **nf-core GitHub Actions workflows we don't use (6):** `branch.yml`, `ci.yml`, `linting.yml`,
  `linting_comment.yml`, `awstest.yml`, `awsfulltest.yml`.
- **Other template files we replace or omit:** `.github/.dockstore.yml`, `.gitattributes`,
  `CHANGELOG.md`, `CODE_OF_CONDUCT.md`, the email/sendmail templates and logo assets under
  `assets/` and `docs/images/`, `conf/test_full.config`, and `ro-crate-metadata.json`.

Every other required file is still enforced.

`branch.yml`, `ci.yml`, `linting.yml`, and `linting_comment.yml` have no dedicated lint rule of their own, so they can only be excluded via the `files_exist` list. The files that are *not* exempted — `main.nf`, `nextflow.config`, `conf/base.config`, the root `README.md`, and the module files — are still enforced.
