# BiodivPipeline

A modular nf-core / Nextflow pipeline that turns raw biodiversity CSV records into a
quality-annotated, taxonomically resolved dataset and FAIR RDF triples.

**Framework:** [nf-core](https://nf-co.re) template v4.0.2

## Quick start

**Prerequisites:** Java 11+, [Nextflow](https://www.nextflow.io/) ≥ 24.x, [Docker](https://www.docker.com/) running.

```bash
# 1. Set the module API keys (what each is for: docs/runbook/running.md#secrets)
nextflow secrets set WP2_BIODIV_API_KEY '<BiodivPortal key>'
nextflow secrets set WP3_OPENAI_API_KEY '<OpenAI key>'
nextflow secrets set WP4_OPENAI_API_KEY '<OpenAI key>'
nextflow secrets set WP5_LLM_API_KEY '<OpenAI-compatible key>'

# 2. Run the bundled test dataset (add ,emulate_amd64 on Apple Silicon)
nextflow run main.nf -profile test,docker --outdir results

# 3. Run your own data
nextflow run main.nf -profile docker --input path/to/biodiv.csv --outdir results
```

No WP5 key? Add `--skip_provisional_concepts`.

Full run guide, secrets, and parameters: **[docs/runbook/running.md](docs/runbook/running.md)**.

## Project structure

```
main.nf                       # entry point
workflows/biodivpipeline.nf   # workflow DAG
modules/local/                # one module per work package
conf/                         # config profiles
docs/                         # documentation (see below)
```

## Documentation

Start at the [documentation index](docs/README.md):

- [Runbook](docs/runbook/running.md) — run, operate, troubleshoot
- [Development](docs/development/developer-guide.md) — contribute and add modules
- [Reference](docs/reference/architecture.md) — architecture and module interfaces

Built on [nf-core](https://nf-co.re) — see [`CITATIONS.md`](CITATIONS.md).
