# Troubleshooting

## A module fails to pull its image (`unauthorized` / `denied`)

The module images live under `ghcr.io/biodivportal/*`, published by CI
(`.github/workflows/docker-publish.yml`). Each module's `main.nf` `container` directive points
at its canonical `biodivportal` ref. These org packages are currently **private**, so a pull
fails on any machine that is not authenticated or lacks read access to the package.

Resolve it one of two ways:

- **Preferred (zero-auth):** a biodivportal org admin sets the module packages to **Public** (or
  links them to the `BiodivPipeline` repo with inherited read access). Anonymous pulls then work
  out of the box.
- **Until then:** authenticate before running —
  `echo <PAT> | docker login ghcr.io -u <username> --password-stdin` with a token that has the
  `read:packages` scope and access to the packages.

## `No matching manifest for linux/arm64` (Apple Silicon)

The published module images are multi-arch (`linux/amd64` + `linux/arm64`), so this should
not occur normally. If it does — e.g. a stale local tag or a hand-built amd64-only image —
force emulation: `-profile test,docker,emulate_amd64`.

## A rebuilt image fails with `No module named 'app'` (or similar)

A locally rebuilt image overwrote a working tag with a broken build. The registry copy
still works — remove the local one and re-pull:

```bash
docker rmi -f ghcr.io/<owner>/<image>:<tag>
docker pull ghcr.io/<owner>/<image>:<tag>
```

Do not rebuild the published module images unless you intend to fix and push them.

## `Access to undefined parameter provisional_concepts_*_col`

Cosmetic WARN lines from WP5's module (params it declares but the pipeline doesn't set).
Safe to ignore; they do not affect the run.

## RDF (WP7) is skipped

`--skip_rdf` defaults to `true`. RDF needs an RML mapping whose columns match the dataset
(a WP8 Schema Editor deliverable). Because `skip_rdf` is not in `nextflow_schema.json`,
`--skip_rdf false` on the CLI is ignored (it becomes the truthy string `"false"`) — enable
it from a params-file instead:

```yaml
# rdf-params.yaml
skip_rdf: false
mapping_schema: <real RML>
```

```bash
nextflow run main.nf -profile docker --input your.csv -params-file rdf-params.yaml --outdir results
```

## A step aborts

Read the tail of `.nextflow.log`, then the failing task's `work/<xx>/<hash>/.command.err`
(the path is printed in the error). `-resume` re-runs only the failed and downstream steps.
