# BiodivPipeline — Lint Configuration Decisions

## Context

nf-core lint is designed for production pipelines with GitHub Actions CI, AWS test runs, and nf-core registry releases. We are not using CI for now and are not publishing to the nf-core registry, so most of these tests don't apply.

## Disabled Rules

| Rule | Reason |
|------|--------|
| `actions_awsfulltest` | No AWS infrastructure (no cloud) |
| `actions_awstest` | No AWS infrastructure |
| `actions_nf_test` | Not using CI for now |
| `actions_schema_validation` | Not using CI for now |
| `files_unchanged` | Template files are intentionally customised for this project |
| `files_exist` (partial) | 4 GitHub Actions workflow files excluded; all other required files still enforced |
| `pipeline_todos` | TODOs are intentional during development — re-enable before final submission |
| `multiqc_config` | Pipeline doesn't use MultiQC; custom per-step quality reports used instead |
| `rocrate_readme_sync` | Not publishing to nf-core registry |
| `modules_json` | All modules are written locally (`modules/local/`), none imported from nf-core registry |

## Note on `files_exist`

`branch.yml`, `ci.yml`, `linting.yml`, and `linting_comment.yml` have no dedicated lint rule of their own, so they can only be excluded via the `files_exist` list. All other required files (README, nextflow.config, main.nf, Dockerfile, CHANGELOG, docs/, conf/base.config) remain enforced.