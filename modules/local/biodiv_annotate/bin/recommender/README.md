# WP2.5 – Ontology Recommender

Maps CSV columns to suitable ontologies using the [GFBio Biodiversity Portal Recommender API](https://biodivportal.gfbio.org/recommender). For each column, sample values (row contents) are assembled into a single request and sent to the API. Results are written to a CSV overview and a JSON config for use by other work packages but especially the Annotator from WP2.

---

## Setup
Install dependencies:
```bash
pip install requests deep-translator
```
Set your API key as an environment variable in your terminal:
```bash
# Linux / macOS (persists for the session)
export BIODIV_API_KEY=your_api_key_here

# Windows PowerShell
$env:BIODIV_API_KEY = "your_api_key_here"

# Windows CMD
set BIODIV_API_KEY=your_api_key_here
```
---
## Usage
By default the script expects the input CSV at `data/Belege_aus_D.csv` and writes outputs to `output/`. Both can be overridden via CLI arguments:
```bash
python wp2_5_ontology_recommender.py --csv path/to/your_file.csv --output path/to/output_dir/
```
Both arguments are optional with fallback default values.

---

## How It Works
For each column the script samples `SAMPLE_SIZE` many rows, builds a request sentence and sends it to the API. If the score is too low, it retries with an English translation just for testing. The result is classified as `use` (≥ 0.6), `review` (≥ 0.4), or `skip` (< 0.4), which could be lowered later on.

---

## Outputs
Output files are written to the directory specified by `--output` (default: `output/`). The directory is created automatically if it doesn't exist.
| File | Description |
|---|---|
| `column_ontology_mapping.csv` | Per-column overview: decision, top-3 ontologies, scores |
| `ontology_config.json` | Structured config for downstream WPs (`use` and `review` columns only) |
---
## Further Information
1. As for now we use this script to build the outputs by running it manually once. The script could be directly integrated into the pipeline at any time, the `--csv` and `--output` flags make it easy to plug in.
2. We recommend letting an expert review the outputs since we only rely on the Recommender API, which could lead to wrong recommendations depending on the dataset quality.
3. Especially fields like `Locality` are very mixed when it comes to ontologies (GeoNames, ENVO, ...).