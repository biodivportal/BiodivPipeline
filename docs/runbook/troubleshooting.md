# Troubleshooting

## A module fails to pull its image (`unauthorized` / `denied`)

Some module images live in private personal registries (currently WP5
`ghcr.io/dabauer/wp5` and the WP7 RDF service). Build them locally instead and point the
run at the local build with an override config:

```bash
docker build --platform linux/amd64 -t wp5-provisional-concepts:local \
    modules/local/provisional_concepts/bin

nextflow run main.nf -profile test,docker,emulate_amd64 \
    -c conf/local_images.config --outdir results
```

`conf/local_images.config` maps the process to the local image. Long-term fix: the module
team makes the image public.

## `No matching manifest for linux/arm64` (Apple Silicon)

The demo images are `linux/amd64`-only. Add the emulation profile:
`-profile test,docker,emulate_amd64`.

## A rebuilt image fails with `No module named 'app'` (or similar)

A locally rebuilt image overwrote a working tag with a broken build. The registry copy
still works — remove the local one and re-pull:

```bash
docker rmi -f ghcr.io/<owner>/<image>:<tag>
docker pull --platform linux/amd64 ghcr.io/<owner>/<image>:<tag>
```

Do not rebuild the WP3/WP4/WP6 `:demo` images unless you intend to fix and push them.

## `Access to undefined parameter provisional_concepts_*_col`

Cosmetic WARN lines from WP5's module (params it declares but the pipeline doesn't set).
Safe to ignore; they do not affect the run.

## RDF (WP7) is skipped

`--skip_rdf` defaults to `true`. RDF needs an RML mapping whose columns match the dataset
(a WP8 Schema Editor deliverable) and a pullable service image. Enable with
`--skip_rdf false --mapping_schema <real RML>`.

## A step aborts

Read the tail of `.nextflow.log`, then the failing task's `work/<xx>/<hash>/.command.err`
(the path is printed in the error). `-resume` re-runs only the failed and downstream steps.
