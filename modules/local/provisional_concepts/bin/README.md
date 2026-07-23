# WP5 - Provisional Concepts Module

This directory contains the core logic for the **Provisional Concepts (WP5)** pipeline module.

Locality resolution is a LLM split/translate → ENVO retrieval (embeddings + reranker) → LLM judge. Each locality ends up `ACCEPT` (matched an ENVO term), `REGISTER` (a habitat concept missing from ENVO, with a generated definition), or `DISCARD` (no habitat term). If the input has an upstream CLC (Corine Land Cover) hint (`llm_code`/`llm_name`/`llm_confidence`), it's passed to the judge.

## Relevant Scripts

- `main.py`: Core CLI orchestrator. It ingests unresolved terms, routes them to the appropriate resolvers, writes both JSON and CSV output files, and optionally runs evaluation.
- `export_csv.py`: Contains the CSV export logic. Can also be run standalone to convert any concept JSON file back to CSV.
- `evaluate.py`: Evaluation utility script for measuring resolver performance (precision, recall, top-k accuracy) against a ground-truth dataset.
- `clients/local_geonames.py`: Script to download and prepare local GeoNames data for offline country/locality filtering.

## Outputs

Running the resolver orchestrator (`main.py`) always generates two output formats:
- **JSON Output** (`.json`): A fully detailed machine-readable payload containing all raw and intermediate resolving metadata (e.g., taxonomic hierarchies, full API payloads, and LLM split details).
- **CSV Output** (`.csv`): A readable, exhaustive flat summary of the resolved concepts. Unified columns are used for both taxon and locality records, and type-specific details are flattened into semicolon-separated `key=value` pairs.

## Usage

### 1. Run the Resolver Standalone
Execute the orchestrator directly to resolve taxonomic (species) and/or geographic (locality) concepts. Both are enabled by default; use the skip flags if you want to bypass either resolver:
```bash
# Run both resolvers (requires WP5_OPENAI_API_KEY)
python main.py \
    --input unresolved_terms.csv \
    --output provisional_concepts.json

# Run only species resolution (skips localities, no LLM required)
python main.py \
    --input unresolved_terms.csv \
    --output provisional_concepts.json \
    --skip-localities
```
The matching CSV output will automatically be created at `provisional_concepts.csv`. You can customize the CSV output path using the `--csv-output` flag.

### 2. Run with Evaluation
To run the resolver and immediately evaluate the locality results against a ground truth dataset:
```bash
python main.py \
    --input unresolved_terms.csv \
    --output provisional_concepts.json \
    --evaluate \
    --ground-truth data/provisional_concepts_ground_truth.csv \
    --eval-output data/evaluation_results.json
```
To enable splitting evaluation (which compares the LLM location/environment split against the ground truth, requiring LLM API calls), add the `--enable-splitting-eval` flag.

#### Required Ground Truth Fields
The ground truth CSV must contain the following columns:
- `original_term`: The raw unresolved locality/environment text string.
- `split_location`: The expected location/geographic place parsed.
- `split_environment`: The expected environment/habitat parsed.
- `matched_environment_envo_uri`: The expected ENVO term URI.
- `environment_decision`: The expected action: `ACCEPT` or `REGISTER`.

### 3. Pre-download GeoNames Data
GeoNames datasets default to Germany (`DE`) on first load. You can pre-download specific country maps for offline resolution:
```bash
# Download Germany (DE)
python clients/local_geonames.py

# Download Austria (AT) and Switzerland (CH)
python clients/local_geonames.py AT CH
```

## Docker Integration

### Build the Image
The ENVO term set + embeddings are produced by a separate single-arch **data image** (`Dockerfile.data`) and copied into the runtime image at build time (see [Baked Assets](#baked-assets-in-the-dockerfile)). CI builds the data image automatically; for a local build you do it in two steps from this `bin/` directory:
This is only because precomputing the embeddings saves on start-up time but the GH build is too slow on arm64.

**1. Build the data image** (fetches the ENVO term set from OLS and encodes it — fast on native CPU, and skipped entirely if `data/envo_embeddings.pkl` already exists locally):
```bash
docker build -t ghcr.io/biodivportal/provisional-concepts-data:0.4 -f Dockerfile.data .
```

**2. Build the runtime image:**

**CPU version (default):**
```bash
docker build -t ghcr.io/biodivportal/provisional-concepts:0.4 -f Dockerfile .
```

**GPU version (uses PyTorch CUDA 12.6 wheels):**
```bash
docker build --build-arg DEVICE=gpu -t ghcr.io/biodivportal/provisional-concepts:0.4-gpu -f Dockerfile .
```

### Run the Image Standalone
To run the container standalone (which defaults to running the resolver script):

**CPU version:**
```bash
# Mount a local folder containing your data to /data inside the container
docker run -it --rm \
    -v /absolute/path/to/local/data:/data \
    -e WP5_OPENAI_API_KEY="your-key-here" \
    ghcr.io/biodivportal/provisional-concepts:0.4 \
    --input /data/unresolved_terms.csv \
    --output /data/provisional_concepts.json
```

**GPU version:**
Running with GPU support requires the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) installed on the host machine.
```bash
docker run -it --rm --gpus all \
    -v /absolute/path/to/local/data:/data \
    -e WP5_OPENAI_API_KEY="your-key-here" \
    ghcr.io/biodivportal/provisional-concepts:0.4-gpu \
    --input /data/unresolved_terms.csv \
    --output /data/provisional_concepts.json
```

### Baked Assets in the Dockerfile
To reduce startup times some data is baked into the docker image.
1. **Local GeoNames database** (Germany `DE` and `admin1CodesASCII` maps).
2. **HuggingFace embedding + reranker models** (`BAAI/bge-large-en-v1.5` and `BAAI/bge-reranker-v2-m3`).
3. **ENVO term cache and embeddings** — pulled from OLS and precomputed by the separate `provisional-concepts-data` image (`Dockerfile.data`), then copied into the runtime image. Building them in a single-arch (amd64) image avoids re-encoding the 3,872-term set per platform under QEMU, which previously blew past the CI 6h limit. CI publishes the data image as `ghcr.io/biodivportal/provisional-concepts-data:<version>`; it can stay private since only the authenticated CI build pulls it, and it only needs rebuilding when the ENVO term set or `EMBEDDING_SCHEME` in `resolvers/locality/envo_matching.py` changes.
