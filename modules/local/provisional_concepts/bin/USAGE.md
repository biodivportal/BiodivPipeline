# Using WP5

This guide explains how to run the provisional concepts resolver locally or within a Docker container.

## Prerequisites

- Python 3.10 or higher (or Docker)
- `WP5_OPENAI_API_KEY`: Required for the LLM splitting, translation, and judging stages. If you are only resolving plant names, you can pass `--skip-localities` to run without an API key.
- Python packages listed in `requirements.txt`. The ENVO embeddings will be generated automatically on the first run, or loaded from precomputed caches in Docker.

## Quick start

Create a virtual environment and install the required dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the pipeline on your input CSV:

```bash
python main.py --input unresolved_terms.csv --output provisional_concepts.json
```

A companion CSV file named `provisional_concepts.csv` will be saved in the same directory. You can specify a custom location using the `--csv-output` flag.

## Running on targeted data

To resolve only plant taxa and bypass LLM calls:

```bash
python main.py --input unresolved_terms.csv --output provisional_concepts.json --skip-localities
```

To resolve only locality strings:

```bash
python main.py --input unresolved_terms.csv --output provisional_concepts.json --skip-species
```

## Input schema and column mapping

The input schema is flexible and configurable. The resolver is not restricted to the standard BGBM `unresolved_terms.csv` format; it can process any CSV containing similar columns by mapping header names via CLI flags or a mapping file. The column resolution logic lives in `ingest.py` (`resolve_mapping` and `split_resolvers`).

### Expected columns

| Logical column | Default header | Target resolver | Required |
|---|---|---|---|
| id | `HerbariumID` | Output join key | Yes |
| unresolved terms | `unresolved_fields` | Record routing | No |
| family | `Family` | Plant resolver | No |
| genus | `Genus` | Plant resolver | No |
| name | `NameCache` | Plant resolver | No |
| fullname | `FullNameCache` | Plant resolver | No |
| locality | `Locality`, `FundortUNdOeko` | Locality resolver | No |
| country | `Country` | Locality context | No |

### How routing works

The `unresolved terms` column (matching WP2's comma-separated list in `unresolved_fields`) determines routing for each record. Fields matching plant taxon headers are routed to the plant resolver. Fields matching locality headers are sent to the locality resolver. If this column is missing or empty, the record is evaluated by both resolvers.

### Custom column mappings

You can override individual column headers using command-line flags:

```bash
python main.py --input my_data.csv --output out.json \
    --id-col record_id --locality-col Site --locality-col Habitat --country-col Nation
```

Common mapping flags:
- `--mapping`: Path to a JSON configuration file containing full column mappings.
- `--id-col`: Header name for the record identifier.
- `--unresolved-terms-col`: Header name for the unresolved fields list.
- `--family-col`, `--genus-col`, `--name-col`, `--fullname-col`: Header names for taxonomy fields.
- `--locality-col`: Header name for locality and habitat fields (can be specified multiple times).
- `--country-col`: Header name for country information.

## Available options

| Flag | Description |
|---|---|
| `--input`, `--output` | Input CSV path and output JSON path |
| `--csv-output` | Output CSV path (defaults to same folder as output JSON) |
| `--ontology-config` | Configuration file for ontology weights (default: `ontology_config.json`) |
| `--limit` | Process only the first N rows for testing |
| `--skip-localities` | Skip locality and ENVO resolution (taxa only, no LLM calls) |
| `--skip-species` | Skip plant taxonomy resolution |
| `--evaluate` | Evaluate locality matches against a ground truth file |
| `--ground-truth`, `--eval-output` | Ground truth CSV path and evaluation results output path |
| `--enable-splitting-eval` | Also evaluate the LLM splitting step against ground truth |

## Running evaluation

You can evaluate resolution accuracy against a ground truth file:

```bash
python main.py --input unresolved_terms.csv --output provisional_concepts.json \
    --evaluate \
    --ground-truth data/provisional_concepts_ground_truth.csv \
    --eval-output data/evaluation_results.json
```

Required ground truth columns include `original_term`, `split_location`, `split_environment`, `matched_environment_envo_uri`, and `environment_decision` (ACCEPT or REGISTER).

## Local GeoNames data

The place name resolver relies on offline GeoNames data, defaulting to Germany:

```bash
python clients/local_geonames.py
```

To fetch data for other countries by two-letter country code:

```bash
python clients/local_geonames.py AT CH
```

## Running with Docker

ENVO terms and embeddings are built into a separate single-architecture data image to prevent long encoding times during container startup.

1. Build the data image (fetches ENVO terms from OLS and computes embeddings):

```bash
docker build -t ghcr.io/biodivportal/provisional-concepts-data:0.4 -f Dockerfile.data .
```

2. Build the runtime image (CPU by default):

```bash
docker build -t ghcr.io/biodivportal/provisional-concepts:0.4 -f Dockerfile .
```

For GPU acceleration:

```bash
docker build --build-arg DEVICE=gpu -t ghcr.io/biodivportal/provisional-concepts:0.4-gpu -f Dockerfile .
```

3. Run the container:

```bash
docker run -it --rm \
    -v /absolute/path/to/data:/data \
    -e WP5_OPENAI_API_KEY="your-key" \
    ghcr.io/biodivportal/provisional-concepts:0.4 \
    --input /data/unresolved_terms.csv --output /data/provisional_concepts.json
```

For GPU execution, ensure the NVIDIA Container Toolkit is installed and pass `--gpus all` along with the GPU image tag.

## Understanding the output

Every row receives a disposition action: ACCEPT, REGISTER, or DISCARD (or REVIEW for taxa). Matched ENVO terms or GBIF usage records are stored in the `match_*` columns. When a concept is marked for registration, generated definitions and synonyms are populated in `definition` and `proposed_synonyms`.

## Additional documentation

- [Component overview](docs/README.md): Details on the LLM splitter, GeoNames resolver, ENVO matcher, and plant taxa resolver.
- [Evaluation and performance](docs/research/evaluation.md): Results and benchmark analysis across datasets.
- [Decisions and lessons](docs/research/decisions.md): Architecture choices and trade-offs.
