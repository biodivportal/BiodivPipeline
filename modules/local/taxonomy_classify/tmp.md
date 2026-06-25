# TAXONOMY_CLASSIFY (BiodivPipeline module)

The WP3 land-cover and plant-taxonomy classifier, packaged as a Nextflow module for the BiodivPipeline nf-core workflow. It classifies each biodiversity record against CORINE Land Cover (CLC) habitat categories (via an LLM) and resolves its scientific name against the GBIF backbone, emitting a single enriched CSV.

This module wraps the same classifier that is also available as a standalone service. Here it runs as a one-shot batch step inside the pipeline rather than as a long-running service. There is no FastAPI app in this context (`main.py` is omitted). Nextflow drives the batch CLI (`classify.py`) directly, and the module is not run independently. It executes as part of `nextflow run`, or in isolation via `nf-test` for development.

## Module Structure

```
modules/local/taxonomy_classify/
├── main.nf                   # Nextflow process definition
├── Dockerfile                # builds the task image
├── requirements.txt
├── app/                      # baked into the image
│   ├── classify.py           # CLI entry point Nextflow invokes
│   ├── pipeline.py
│   ├── process.py
│   ├── land_classifier.py    # in-process LLM land classifier
│   ├── taxonomy_lookup.py    # GBIF lookup, with in-memory cache
│   ├── models.py
│   ├── config.py
│   └── taxonomy.csv
└── tests/
    ├── main.nf.test
    └── sample10.csv          # fixture
```

The classification logic is identical to the standalone service. The only differences are the absence of `main.py` and that the entry point is invoked by Nextflow rather than a user.

## Pipeline Role

The module sits in the workflow after the annotation step:

```
COLUMN_STANDARDISE → BIODIV_ANNOTATE → TAXONOMY_CLASSIFY → RDF_TRANSFORM
```

It receives the enriched CSV produced before and must read the original BGBM columns (`HerbariumID`, `FullNameCache`, `Genus`, `Family`, `Locality`, `FundortUNdOeko`).

**Output:**

- `resolved`: `taxonomy_resolved.csv`, the enriched records (CLC + GBIF columns)
- `versions`: `versions.yml`

The output filename and emit names are fixed by the workflow and must not be renamed.

## Requirements

- Nextflow
- Docker
- An OpenAI API key, provided as a Nextflow secret (see below)
- `nf-test` (for module testing)

## Building the Image

The module references a locally built image (`container 'taxonomy-classify:0.1'`):

```bash
cd modules/local/taxonomy_classify
docker build -t taxonomy-classify:0.1 .
```

For local runs, Nextflow's default registry prefix must be disabled so the unqualified image name resolves to your local build. This is set in the test config (`docker.registry = ''`); the same applies to the main config for local pipeline runs. For shared use, push the image to a registry and update the `container` directive accordingly.

## Providing the API Key

The process declares `secret 'OPENAI_API_KEY'`, which keeps the key out of logs and `.command.sh`. Register it once:

```bash
nextflow secrets set OPENAI_API_KEY "sk-your-key-here"
```

## Running

The module in isolation, via nf-test:

```bash
nf-test test modules/local/taxonomy_classify/tests/main.nf.test
```

## Output Columns

`taxonomy_resolved.csv` contains one row per input record:

| Column | Description |
|--------|-------------|
| `id` | Record identifier, for joining with input data |
| `clc_code` | CLC Level-3 code (e.g. `311`) |
| `clc_name` | CLC category name (canonical, from the code) |
| `clc_confidence` | LLM match confidence, `0.0`-`1.0` |
| `clc_reason` | LLM explanation for the match |
| `clc_input` | The text that was classified |
| `clc_source` | Model used (`openai` or `ollama`) |
| `clc_field` | Whether `FundortUNdOeko` or `Locality` was used |
| `taxon_identifier` | GBIF backbone key |
| `taxon_confidence` | GBIF match confidence, `0`-`100` |
| `taxon_status` | `resolved`, `fuzzy`, `unresolved`, or `error` |
| `error` | Any error encountered while processing the row |

> `clc_confidence` (0.0-1.0) and `taxon_confidence` (0-100) are on different scales.

## Notes

- The LLM is called once per record; at large dataset sizes, OpenAI cost and runtime scale accordingly.
- GBIF results are cached in memory within a single task; the cache does not persist across runs.
- A `taxon_status` of `error` indicates a transient GBIF failure, distinguishable from a genuine `unresolved` no-match.
- Ollama is supported but external and not the production target; for pipeline use, OpenAI is assumed.

## Planned Extensions

- Cross-run persistence of the GBIF cache
- Recording the GBIF match rank (species / genus / family)
- Creation of cache for LLM calls

## AI Assistance

This module was developed with the assistance of Claude for architectural guidance, code review, and documentation. All code has been reviewed and tested by the authors.