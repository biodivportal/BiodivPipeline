# WP6 Column-Mapping-Microservice — Technical Documentation

**Module:** `app/` (FastAPI service, matching pipeline, CLI)
**Purpose:** Automatically maps arbitrary CSV column headers to standardized ABCD 3.0 terms.

---

## Table of Contents

1. [How to Run](#1-installation--how-to-run)
2. [Pipeline Documentation](#2-pipeline-documentation)
3. [Weights — What They Do and How to Change Them](#3-weights--what-they-do-and-how-to-change-them)
4. [Configuration Files](#4-configuration-files)
5. [API Reference](#5-api-reference)
6. [CLI Reference](#6-cli-reference)
7. [LLM Integration](#7-llm-integration)
8. [Do Results Seem Reasonable?](#8-do-results-seem-reasonable)


---

## 1. How to Run

**Prerequisites:** Python 3.10+, Docker (optional)

### Without Docker (Local)

**Installation:**
```bash
# Install all dependencies
make install
# or manually:
pip install -r requirements.txt
```

The first time the pipeline runs, it downloads the embedding model
`intfloat/multilingual-e5-small` (~470 MB) automatically from HuggingFace.
This only happens once; the model is cached locally afterwards.

**Run as a REST API:**
```bash
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
```

Then open [http://localhost:8000/docs](http://localhost:8000/docs) for the
interactive Swagger UI where you can test all endpoints directly in the browser.

**Run as a CLI (without starting the web server):**
```bash
python -m app.standardize \
  --input raw.csv \
  --out-csv standardised.csv \
  --out-map column_mapping.json
```

This reads a CSV file, runs the full mapping pipeline, and writes:
- `standardised.csv` — the original CSV with renamed column headers
- `column_mapping.json` — detailed mapping results including confidence scores

### With Docker

**Installation (Build image):**
```bash
make docker
```

**Run as a REST API:**
```bash
make run
# API is now available at http://localhost:8000
```

### Health Check

```bash
curl http://localhost:8000/health
# {"status": "healthy", "pipeline_ready": true, "version": "1.0.0"}
```

---

## 2. Pipeline Documentation

This document describes the complete mapping pipeline from input to output,
step by step, with the theoretical background behind each decision.

---

### Overview

The goal of the pipeline is to take an arbitrary CSV column header — which may
be in German, English, abbreviated, or inconsistently named — and return the
most likely matching term from the ABCD 3.0 biodiversity schema.

The pipeline combines five complementary matching strategies into a single
weighted score, ranks all candidate ABCD terms by that score, and adds a
confidence estimate so that uncertain predictions can be flagged for human review.

```
CSV file
   │
   ▼
Column headers extracted
   │
   ▼
┌──────────────────────────────────────────────────────────┐
│                   MAPPING PIPELINE                       │
│                                                          │
│  For each header:                                        │
│                                                          │
│  ┌─────────────────┐                                     │
│  │ 1. Normalization│                                     │
│  └────────┬────────┘                                     │
│           │                                              │
│  ┌────────▼────────┐                                     │
│  │ 2. Embedding    │   ← header encoded as query vector  │
│  └────────┬────────┘                                     │
│           │                                              │
│  ┌────────▼──────────────────────────────────────┐       │
│  │ 3. Scoring against all ABCD candidate terms   │       │
│  │                                               │       │
│  │   semantic_score       (embedding similarity) │       │
│  │   surface_string_score (fuzzy name matching)  │       │
│  │   term_string_score    (fuzzy term matching)  │       │
│  │   heuristic_bonus      (keyword rules)        │       │
│  │   profile_boost        (column value analysis)│       │
│  └────────┬──────────────────────────────────────┘       │
│           │                                              │
│  ┌────────▼────────┐                                     │
│  │ 4. Weighted sum │  → final_score per candidate        │
│  └────────┬────────┘                                     │
│           │                                              │
│  ┌────────▼────────┐                                     │
│  │ 5. Ranking      │  → top-N candidates returned        │
│  └────────┬────────┘                                     │
│           │                                              │
│  ┌────────▼────────┐                                     │
│  │ 6. Confidence   │  → confidence score + review flag   │
│  └─────────────────┘                                     │
│                                                          │
└──────────────────────────────────────────────────────────┘
   │
   ▼
JSON response with predicted ABCD term,
confidence score, and optional review flag
```

---

### Before the Pipeline Starts: Candidate Preparation

**File:** `app/matching/pipeline.py` → `_load_candidates()`

Before any header is processed, the pipeline loads all possible ABCD terms
it can match against. This happens once at startup.

**Sources:**
- `data/abcd.json` — the official ABCD 3.0 schema, containing every standardized
  term and its definition (e.g. `LatitudeDecimal`, `GatheringAgentsText`, etc.)
- `app/config/profiling_targets.json` — a manually curated list of synonyms and
  alternative surface forms for each ABCD term (e.g. `latitude`, `lat`, `Breitengrad`
  are all surface forms for `LatitudeDecimal`)

Each ABCD term is expanded into all its known surface forms. Every surface form
is normalized and pre-encoded into a vector embedding at startup, so that
matching at request time is fast.

---

### Step 1 — Normalization

**File:** `app/matching/string_matching.py` → `normalize_text()`

The raw column header is normalized before any comparison takes place.
This step handles the most common sources of mismatch between real-world
column names and standardized ABCD terms.

**What happens:**

1. **CamelCase splitting:** `CollectionDateBegin` → `collection date begin`
2. **Lowercasing:** `Sammlerteam` → `sammlerteam`
3. **German-to-English replacement** of known domain terms:

   | Input term       | Normalized output              |
   |------------------|-------------------------------|
   | `sammlerteam`    | `collector team`               |
   | `sammler`        | `collector`                    |
   | `sammelnummer`   | `collection number`            |
   | `bild`           | `image`                        |
   | `db`             | `database`                     |
   | `fundort`        | `locality`                     |
   | `oeko` / `öko`   | `ecology habitat`              |
   | `lat`            | `latitude`                     |
   | `lon` / `lng`    | `longitude`                    |
   | `uri`            | `uri link`                     |
   | `anmerkungen`    | `notes remarks comments`       |
   | `titeletikett`   | `label title text`             |
   | `expeditionsangabe` | `project expedition survey` |

4. **Special character removal:** only letters, digits, umlauts, and spaces remain
5. **Whitespace normalization:** multiple spaces collapsed to one

**Why this matters:** The embedding model works better with clean, English-language
text. Normalizing German abbreviations and compound words before encoding
dramatically improves semantic similarity for domain-specific terms.

---

### Step 2 — Header Embedding

**File:** `app/matching/semantic_matching.py` → `get_header_embeddings()`

The normalized header is encoded into a dense vector using the
`intfloat/multilingual-e5-small` sentence transformer model.

The model expects a specific prefix format:
- Headers are encoded as **queries**: `"query: collection date begin"`
- Candidate surface forms are encoded as **passages**: `"passage: collection date"`

This asymmetric query/passage encoding is built into the E5 model architecture
and is what makes it suitable for retrieval tasks — the model is trained to
place semantically related queries and passages close together in vector space,
even if they use different words.

All candidate surface form embeddings are computed once at startup and reused
for every request.

---

### Step 3 — Scoring

For each header, five independent signals are computed against every ABCD
candidate term. These signals are complementary — each captures a different
aspect of similarity.

#### Signal 1: Semantic Score

**File:** `app/matching/semantic_matching.py`

Cosine similarity between the header query embedding and each candidate surface
form passage embedding.

For each ABCD term, all surface form similarities are computed, then the
**mean of the top 3** is taken. Using the top-3 mean (instead of just the
maximum) makes the score more robust — a term with several moderately good
surface forms is preferred over one with a single lucky exact match.

```
semantic_score(header, term) = mean_of_top3(
    cosine_similarity(embed(header), embed(surface_form))
    for each surface_form of term
)
```

**Range:** approximately [0, 1]

**Strengths:** Captures meaning across languages and paraphrases.
`Sammlerteam` maps close to `GatheringAgentsText` in vector space even though
the words look nothing alike, because both refer to the concept of a collector.

**Weakness:** Short headers (e.g. `DB`, `Nr`) carry little semantic signal.
This is why the other signals exist.

#### Signal 2: Surface String Score

**File:** `app/matching/string_matching.py` → `string_similarity()`

Fuzzy string similarity between the header and all surface forms of a candidate.

Four RapidFuzz metrics are computed, and the maximum is used:
- `fuzz.ratio` — character-level Levenshtein similarity
- `fuzz.partial_ratio` — best matching substring
- `fuzz.token_sort_ratio` — token similarity, order-independent
- `fuzz.token_set_ratio` — token similarity as sets

Same as the semantic score, the **mean of the top-3 surface form scores** per
ABCD term is used.

**Range:** [0, 1]

**Strengths:** Catches direct matches, abbreviations, and spelling variations.
If someone writes `scientificName` and the surface form is `ScientificName`,
this signal scores very high.

#### Signal 3: Term String Score

**File:** `app/matching/string_matching.py` → `term_string_similarity()`

Same fuzzy matching as Signal 2, but comparing the header directly against the
**canonical ABCD term** (e.g. `LatitudeDecimal`), not its surface forms.

The canonical term is first split with `split_term()` (CamelCase → tokens)
before comparison.

**Range:** [0, 1]

**Strengths:** Useful when the input header already looks like an official ABCD
name, such as `LocalityText` or `FieldNumber`.

#### Signal 4: Heuristic Bonus

**File:** `app/matching/heuristic_matching.py`
**Config:** `app/config/heuristic_rules.json`

A small rule-based bonus added when a specific keyword is present in the
normalized header and the candidate term is a known good match for that keyword.

Each rule in `heuristic_rules.json` has the form:
```json
{
  "header_keyword": "latitude",
  "term_keyword": "latitude",
  "bonus": 0.08
}
```

A bonus is added if `header_keyword` appears in the normalized header AND
either `term_keyword` appears in the split term OR the term is in an explicit
`exact_terms` list.

**Example rules:**

| Header contains | Matching ABCD terms | Bonus |
|----------------|---------------------|-------|
| `latitude`     | terms with `latitude` | 0.08 |
| `longitude`    | terms with `longitude` | 0.08 |
| `country`      | terms with `country` | 0.05 |
| `genus`        | terms with `genus`   | 0.05 |
| `image`        | `FileURL`, `Image`, `MultimediaObject` | 0.04 |
| `collector`    | `GatheringAgentsText`, `GatheringAgents`, `CollectorName` | 0.04 |
| `database`     | `SourceID`, `DataSet`, `DataSets` | 0.04 |

**Range:** [0, ~0.16] (multiple rules can match)

**Why this exists:** Some concepts are hard to match purely from text similarity.
Geographical coordinates in particular (a column named `Lat` is clearly a
latitude, but the string `Lat` looks nothing like `LatitudeDecimal`). Heuristics
provide a targeted, human-defined correction.

#### Signal 5: Profile Boost

**File:** `app/matching/profiling.py`
**Config:** `app/config/profiling_rules.json`, `app/config/profiling_targets.json`

All previous signals look only at the **column name**. The profile boost looks
at the actual **column values** to infer what kind of data the column contains.

**How it works:**

1. Each column's values are evaluated against a set of profiling rules. Each
   rule produces a score between 0 and 1:

   | Rule | What it checks |
   |------|---------------|
   | `latitude` | Values are numeric, in [-90, 90], with decimals |
   | `longitude` | Values are numeric, in [-180, 180], with decimals |
   | `country` | Values match a list of known country names |
   | `date` | Values match date patterns (YYYY-MM-DD, DD.MM.YYYY, etc.) |
   | `url` | Values start with `https://` |
   | `multimedia_url` | Values are URLs pointing to images/media |
   | `scientific_name` | Values match `Genus species` pattern |
   | `genus` | Values match single capitalized words (not country names) |
   | `barcode` | Values match `ABC123456` patterns |
   | `free_text` | Values are long strings with spaces |
   | etc. | |

2. For each candidate ABCD term, `profiling_targets.json` is checked to see
   if that term is a known target for any matching profiling rule.

3. If a match is found, the profile score is converted to a boost:
   ```
   profile_boost = best_matching_profile_score × profile_max_boost
   ```
   where `profile_max_boost` defaults to `0.10`.

**Range:** [0, `profile_max_boost`] (default: [0, 0.10])

**Why this exists:** A column named `X` containing values like `52.4889`,
`48.1351` is almost certainly a latitude column, regardless of the name.
The profile boost allows the pipeline to use this data-level evidence.

---

### Step 4 — Weighted Sum

**File:** `app/matching/pipeline.py` → `run()`

All five signals are combined into a single final score per candidate term:

```
final_score =
    semantic_weight        × semantic_score
  + surface_string_weight  × surface_string_score
  + term_string_weight     × term_string_score
  + heuristic_weight       × heuristic_bonus
  + profile_weight         × profile_boost
```

Default weights from `app/config/weights.json`:

| Signal | Default weight | Rationale |
|--------|---------------|-----------|
| `semantic_weight` | 0.80 | Semantic similarity is the most general and reliable signal |
| `surface_string_weight` | 0.15 | Name matching is important but secondary |
| `term_string_weight` | 0.05 | Only useful when headers already resemble ABCD names |
| `heuristic_weight` | 1.00 | Additive bonus — not scaled down because bonuses are already small (max ~0.08) |
| `profile_weight` | 1.00 | Additive boost — same rationale |

**Special case — exact synonym match:**
If the header exactly matches one of a candidate's registered surface forms
(case-insensitive), the final score is set to `100.0` and confidence to `1.0`,
bypassing the weighted sum entirely. This ensures that manually registered
synonyms always win over any computed score.

---

### Step 5 — Ranking

**File:** `app/matching/pipeline.py` → `run()`

All candidate ABCD terms are sorted by `final_score` in descending order.
The top-N candidates are kept (N = `prediction_length`, default 1, max 10).

The rank-1 candidate is the main prediction.

---

### Step 6 — Confidence and Review Flag

**File:** `app/matching/confidence.py`

After ranking, the pipeline estimates how reliable the top prediction is.
This is based on three components:

#### Confidence Score

```
confidence = 0.55 × margin_component
           + 0.30 × semantic_component
           + 0.15 × support_component
```

**margin_component** measures how clearly rank-1 beats rank-2:
```
margin = final_score_rank1 - final_score_rank2
margin_component = min(margin / 0.10, 1.0)
```
A margin of 0.10 or more gives a full margin score of 1.0.
The margin receives the highest weight (0.55) because empirically it is the
best separator between correct and incorrect predictions.

**semantic_component** measures how strong the semantic signal was:
```
semantic_component = max((semantic_score_rank1 - 0.70) / 0.20, 0.0)
```
Semantic scores below 0.70 contribute nothing. A score of 0.90 gives
a semantic component of `(0.90 - 0.70) / 0.20 = 1.0`.

**support_component** adds up supporting signals:
- +0.15 if `surface_string_score ≥ 0.75`
- +0.15 if `term_string_score ≥ 0.75`
- +0.10 if `profile_boost > 0`
- +0.10 if `heuristic_bonus > 0`

Maximum support component: 0.50 (capped at 1.0 before weighting).

The final confidence score is capped at 1.0.

#### Manual Review Flag

A prediction is flagged for manual review (`review_flag: true`) if at least
one of the following is true:

| Condition | Reason tag | Interpretation |
|-----------|------------|----------------|
| `margin < 0.04` | `small_margin` | Two candidates are nearly tied — the pipeline is uncertain which is correct |
| `confidence < 0.40` | `low_confidence` | The overall evidence for the prediction is too weak |

A mapping can be flagged for both reasons simultaneously.

---

### Optional Step: LLM Validation

**File:** `app/services/llm_service.py`
**Config:** `app/config/llm_prompt.json`

If an LLM provider and API key are supplied, an optional post-processing step
runs after the pipeline ranking.

**What the LLM does:**
It receives the column header, one example value from the column, and the
pipeline's top-N candidate terms with their ABCD descriptions. It selects
the most appropriate term from this shortlist.

**What the LLM does NOT do:**
It does not search the full ABCD schema or invent new terms. It only chooses
from the candidates already produced by the pipeline. This keeps the LLM
grounded and prevents hallucination of non-existent terms.

**Supported providers:** Anthropic (`claude-haiku-4-5`), OpenAI (`gpt-4o-mini`)

```
Pipeline top-N candidates
         │
         ▼
┌─────────────────────────────────────────┐
│  LLM prompt:                            │
│  "Header: Sammlerteam                   │
│   Example value: Schmidt, M.            │
│   Candidates:                           │
│   1. CollectorName: Name of collector   │
│   2. GatheringAgentsText: ...           │
│   Which fits best?"                     │
└─────────────┬───────────────────────────┘
              │
              ▼
         LLM selects best candidate
              │
              ▼
    Replaces rank-1 in response
```

---

### Complete Example

**Input:** A CSV with column header `Sammlerteam`,
values like `Schmidt, M.`, `Müller, K.`

**Step 1 — Normalization:**
`Sammlerteam` → `collector team`
(rule: `sammlerteam` → `collector team`)

**Step 2 — Embedding:**
`"query: collector team"` encoded into a 384-dimensional vector

**Step 3 — Scoring** (top candidates):

| Candidate | semantic | surface_string | term_string | heuristic | profile | final |
|-----------|----------|---------------|-------------|-----------|---------|-------|
| GatheringAgentsText | 0.82 | 0.41 | 0.38 | 0.04 | 0.00 | 0.72 |
| CollectorName | 0.79 | 0.55 | 0.42 | 0.04 | 0.00 | 0.70 |
| FieldNumber | 0.41 | 0.10 | 0.08 | 0.00 | 0.00 | 0.34 |

(scores are illustrative, not exact measurements)

**Step 4 — Weighted sum:**
```
GatheringAgentsText: 0.8×0.82 + 0.15×0.41 + 0.05×0.38 + 1.0×0.04 + 1.0×0.00
                   = 0.656 + 0.062 + 0.019 + 0.04 = 0.777
```

**Step 5 — Ranking:**
`GatheringAgentsText` ranked #1, `CollectorName` ranked #2

**Step 6 — Confidence:**
```
margin = 0.777 - 0.724 = 0.053
margin_component = min(0.053 / 0.10, 1.0) = 0.53
semantic_component = (0.82 - 0.70) / 0.20 = 0.60
support_component = 0.10 (heuristic bonus present)

confidence = 0.55×0.53 + 0.30×0.60 + 0.15×0.10
           = 0.292 + 0.18 + 0.015 = 0.487
```

`margin (0.053) ≥ 0.04` ✓
`confidence (0.487) ≥ 0.40` ✓
→ `review_flag: false`

**Output:**
```json
{
  "header": "Sammlerteam",
  "predicted_header": "GatheringAgentsText",
  "confidence": 0.487,
  "review_flag": false
}
```


## 3. Weights — What They Do and How to Change Them

### Where weights are defined

**`app/config/weights.json`** — default weights loaded at API startup:

```json
{
  "semantic_weight": 0.8,
  "surface_string_weight": 0.15,
  "term_string_weight": 0.05,
  "heuristic_weight": 1.0,
  "profile_weight": 1.0,
  "profile_max_boost": 0.10
}
```

### What each weight does

| Weight | What it affects | Effect of increasing |
|--------|----------------|----------------------|
| `semantic_weight` | Influence of the embedding model | Favours semantically similar terms even if names differ |
| `surface_string_weight` | Fuzzy match against synonyms/surface forms | Favours near-exact name matches |
| `term_string_weight` | Fuzzy match against the ABCD term itself | Favours headers that look like official ABCD names |
| `heuristic_weight` | Rule-based keyword bonuses | Gives more power to manually defined rules |
| `profile_weight` | Data-value-based boost | Gives more power to content-based detection |
| `profile_max_boost` | Cap on the profile boost | Limits how much profiling can override other signals |

### How to change weights

**Option A — Change the default permanently (no rebuild needed):**

Edit `app/config/weights.json` directly. The API reads this file at startup,
so restart the server (or container) for changes to take effect.

**Option B — Change for a single request (no restart needed):**

Pass weight parameters to the API endpoint or CLI:

```bash
# API (via form field)
curl -X POST http://localhost:8000/standardize \
  -F "file=@raw.csv" \
  -F "semantic_weight=0.6" \
  -F "surface_string_weight=0.3"

# CLI
python -m app.standardize \
  --input raw.csv \
  --out-csv out.csv \
  --out-map map.json \
  --semantic-weight 0.6 \
  --surface-string-weight 0.3
```

Per-request weights override the defaults for that call only.
**No rebuild is required for either option.**

### When to adjust weights

| Situation | Suggested adjustment |
|-----------|----------------------|
| Many headers are abbreviations or typos | Increase `surface_string_weight` |
| Headers are in German or other languages | Keep `semantic_weight` high (default 0.8 is good) |
| Column values are reliable (dates, coords, URLs) | Increase `profile_max_boost` |
| Too many false positives from profiling | Decrease `profile_max_boost` |
| Headers already look like ABCD terms | Increase `term_string_weight` |

---

## 4. Configuration Files

All configuration files are in `app/config/`. **No rebuild is needed** when
these files are changed — the API reads them at startup or request time.

| File | Purpose | Rebuild needed? |
|------|---------|-----------------|
| `weights.json` | Default score weights | Restart server |
| `heuristic_rules.json` | Keyword-based bonus rules | Restart server |
| `profiling_rules.json` | Column-value profiling rules | Restart server |
| `profiling_targets.json` | Synonyms and term mappings | No (API reloads automatically via `/config/synonym`) |
| `llm_prompt.json` | LLM prompt template | No (read per request) |

### Adding a synonym without restarting

```bash
curl -X POST http://localhost:8000/config/synonym \
  -H "Content-Type: application/json" \
  -d '{"target": "LatitudeDecimal", "synonym": "Breitengrad"}'
```

The synonym is saved to `profiling_targets.json` and the pipeline reloads
automatically. The new synonym takes effect immediately for subsequent requests.

---

## 5. API Reference

**Base URL:** `http://localhost:8000`
**Interactive docs:** `http://localhost:8000/docs`

### GET /health

Check if the service is running and the pipeline is ready.

```json
{"status": "healthy", "pipeline_ready": true, "version": "1.0.0"}
```

### POST /standardize

Upload a CSV file and receive column mappings.

**Form parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file` | CSV file | required | The input CSV |
| `prediction_length` | int (1–10) | 1 | How many candidate terms to return per column |
| `semantic_weight` | float | 0.8 | Weight for semantic similarity |
| `surface_string_weight` | float | 0.15 | Weight for surface form string similarity |
| `term_string_weight` | float | 0.05 | Weight for term string similarity |
| `heuristic_weight` | float | 1.0 | Weight for heuristic bonuses |
| `profile_weight` | float | 1.0 | Weight for profiling boost |
| `profile_max_boost` | float | 0.10 | Maximum profiling boost |
| `llm_provider` | string | None | `"anthropic"` or `"openai"` |
| `llm_key` | string | None | API key for the LLM provider |
| `llm_model` | string | None | Model name (defaults: `claude-haiku-4-5` / `gpt-4o-mini`) |

**Response (prediction_length=1):**

```json
{
  "mapping": [
    {
      "header": "HerbariumID",
      "predicted_header": "UnitID",
      "confidence": 0.85,
      "review_flag": false
    }
  ],
  "metadata": {
    "configuration": {
      "semantic_weight": 0.8,
      "..."
    }
  }
}
```

**Response (prediction_length=3):**

```json
{
  "mapping": [
    {
      "header": "HerbariumID",
      "predicted_header": "UnitID",
      "confidence": 0.85,
      "review_flag": false,
      "predictions": ["UnitID", "AccessionNumber", "ID"],
      "confidences": [0.89, 0.81, 0.76]
    }
  ]
}
```

### POST /config/synonym

Add a new synonym for an existing ABCD term. Takes effect immediately.

```json
{"target": "LatitudeDecimal", "synonym": "Breitengrad"}
```

### POST /sync/abcd

Synchronize the local ABCD schema from BioDivPortal. Requires an API key header.

```bash
curl -X POST http://localhost:8000/sync/abcd \
  -H "abcd-api-key: YOUR_KEY"
```

---

## 6. CLI Reference

**Relevant file:** `app/standardize.py`

```bash
python -m app.standardize \
  --input raw.csv \
  --out-csv standardised.csv \
  --out-map column_mapping.json \
  [--top-n 3] \
  [--semantic-weight 0.8] \
  [--surface-string-weight 0.15] \
  [--term-string-weight 0.05] \
  [--heuristic-weight 1.0] \
  [--profile-weight 1.0] \
  [--profile-max-boost 0.10] \
  [--llm-provider anthropic] \
  [--llm-key YOUR_KEY] \
  [--llm-model claude-haiku-4-5]
```

**Via Docker:**

```bash
docker run -v $(pwd):/data mapping-pipeline \
  python -m app.standardize \
  --input /data/raw.csv \
  --out-csv /data/standardised.csv \
  --out-map /data/column_mapping.json
```

---

## 7. LLM Integration

**Relevant files:** `app/services/llm_service.py`, `app/config/llm_prompt.json`

The LLM is an **optional post-processing step** that runs after the pipeline
has already produced its top-N predictions. It does not replace the pipeline —
it selects the best candidate from the pipeline's shortlist.

### How it works

1. Pipeline produces top-N candidate ABCD terms for each header
2. For each header, an LLM prompt is constructed containing:
   - The original header name
   - One example value from the column
   - The top-N candidate terms with their ABCD descriptions
3. The LLM selects the best candidate and returns it as JSON
4. The LLM's choice replaces the pipeline's rank-1 prediction in the output

### Supported providers

| Provider | Default model | Pass as `llm_provider` |
|----------|--------------|------------------------|
| Anthropic | `claude-haiku-4-5` | `"anthropic"` |
| OpenAI | `gpt-4o-mini` | `"openai"` |

### Customizing the prompt

Edit `app/config/llm_prompt.json`. The template uses Python-style `{placeholders}`:
- `{header}` — the column name
- `{example_val}` — an example value from the column
- `{preds_text}` — the numbered list of candidate terms with descriptions

No restart is required — the prompt is read per request.

---

## 8. Do Results Seem Reasonable?

### Evaluation results

Evaluated on 23 annotated column names from `Belege_aus_D.csv`
(ground truth from `Ground_Truth.docx`, including accepted alternatives):

| Metric | Value |
|--------|-------|
| Top-1 Accuracy | 56.5% |
| Top-3 Accuracy | 82.6% |
| Top-5 Accuracy | 87.0% |
| Mean confidence (correct) | 0.69 |
| Mean confidence (wrong) | 0.37 |

### Are these results reasonable?

**Yes, with caveats:**

The 56.5% Top-1 accuracy on this specific test set is affected by an ongoing
fix to the ABCD term naming in the synonym JSON (terms with `has`-prefix like
`hasDate`, `hasCountry` compete with the correct forms). Once resolved, accuracy
is expected to improve.

The **confidence score is a reliable signal**: correct predictions have
significantly higher confidence (0.69) than wrong ones (0.37), confirming that
`review_flag` correctly identifies uncertain mappings.

The **87% Top-5 accuracy** means the correct term appears in the top 5 for
almost all columns — useful when the pipeline is used to suggest candidates
for human review rather than fully automatic mapping.

**Important limitation:** The test set has only 23 entries from a single
dataset. Results on column names from other data providers may differ.
Evaluation on a larger, more diverse annotated set is needed for a conclusive
assessment.
