# WP5 - Provisional Concepts Module

This directory contains the core logic for the **Provisional Concepts (WP5)** pipeline module.

## Relevant Scripts

- `main.py`: Core CLI orchestrator. It ingests unresolved terms, routes them to the appropriate resolvers, and outputs matched/registered concepts.
- `export_csv.py`: Converts the JSON concepts output into a flattened, human-readable CSV.
- `evaluate.py`: Evaluation utility script for measuring resolver performance (precision, recall, top-k accuracy) against a ground-truth dataset.
- `clients/local_geonames.py`: Script to download and prepare local GeoNames data for offline country/locality filtering.

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

### 2. Export Output to CSV
Convert the registered concepts JSON to a readable CSV:
```bash
python export_csv.py \
    --input provisional_concepts.json \
    --output provisional_concepts.csv
```

### 3. Run Evaluation Script
Evaluate performance metrics (precision, recall, top-k match accuracy) against a ground truth dataset:
```bash
python evaluate.py \
    --predictions provisional_concepts.json \
    --ground-truth data/provisional_concepts_ground_truth.csv
```

### 4. Pre-download GeoNames Data
GeoNames datasets default to Germany (`DE`) on first load. You can pre-download specific country maps for offline resolution:
```bash
# Download Germany (DE)
python clients/local_geonames.py

# Download Austria (AT) and Switzerland (CH)
python clients/local_geonames.py AT CH
```

## Docker Integration

### Build the Image
To build the Docker image locally for testing:
```bash
docker build -t ghcr.io/biodivportal/provisional-concepts:0.1 -f Dockerfile .
```

### Run the Image Standalone
To run the container standalone (which defaults to running the resolver script):
```bash
# Mount a local folder containing your data to /data inside the container
docker run -it --rm \
    -v /absolute/path/to/local/data:/data \
    -e WP5_OPENAI_API_KEY="your-key-here" \
    ghcr.io/biodivportal/provisional-concepts:0.1 \
    --input /data/unresolved_terms.csv \
    --output /data/provisional_concepts.json
```

### Baked Assets in the Dockerfile
To reduce startup times some data is baked into the docker image.
1. **Local GeoNames database** (Germany `DE` and `admin1CodesASCII` maps).
2. **HuggingFace Embedding and Reranking models** (`BAAI/bge-large-en-v1.5` and `cross-encoder/ms-marco-MiniLM-L-12-v2`).
