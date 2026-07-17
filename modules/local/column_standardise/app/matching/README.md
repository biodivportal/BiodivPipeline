# Matching Module

This package contains the core logic for mapping input dataset headers to standardized ABCD terms.

The mapping process follows a hybrid approach. It combines semantic similarity, lexical string matching, rule-based heuristics, and column profiling. Each strategy contributes to a weighted final score for every candidate ABCD term. The highest-ranked prediction is then evaluated with a confidence score and may be flagged for manual review.

## Mapping Workflow

1. **Candidate Preparation**
   - ABCD terms are loaded from `data/abcd.json`.
   - Additional surface forms and synonyms are loaded from `profiling_targets.json`.
   - Each candidate consists of a canonical term and one or more surface forms.

2. **Header Processing**
   - Input headers are normalized.
   - German terms and common abbreviations are expanded where possible.
   - Example: `lat` is normalized toward `latitude`, `bild` toward `image`.

3. **Score Calculation**
   - Each input header is compared against all candidate ABCD terms.
   - The pipeline calculates several partial scores:
     - `semantic_score`
     - `surface_string_score`
     - `term_string_score`
     - `heuristic_bonus`
     - `profile_boost`

4. **Ranking**
   - The partial scores are combined into a final score.
   - Candidates are sorted by this score.
   - The highest-ranked candidate becomes the main prediction.

5. **Confidence and Review Decision**
   - The best prediction is compared with the second-best prediction.
   - A confidence score is calculated.
   - Ambiguous or weak predictions are flagged for manual review.

## Score Calculation

The final score is calculated as a weighted sum of all matching signals:

```text
final_score =
    semantic_weight * semantic_score
  + surface_string_weight * surface_string_score
  + term_string_weight * term_string_score
  + heuristic_weight * heuristic_bonus
  + profile_weight * profile_boost
```

The default weights are defined in `app/config/weights.json`.

### Semantic Score

The semantic score measures how close a header is to the candidate surface forms in embedding space.

- Headers are encoded as queries.
- Candidate surface forms are encoded as passages.
- Cosine similarity is calculated between both embedding vectors.
- For each ABCD term, the mean of the three best surface-form similarities is used.

This helps with cases where the wording is different but the meaning is similar.

### Surface String Score

The surface string score compares the input header with all surface forms of a candidate term.

Several RapidFuzz metrics are calculated, and the best result is used. For each candidate term, the mean of the three best surface-form scores is used.

This helps with direct or near-direct matches, abbreviations, and spelling variations.

### Term String Score

The term string score compares the input header directly with the canonical ABCD term.

This is useful when the header already resembles the official ABCD field name.

### Heuristic Bonus

The heuristic bonus is based on manually defined keyword rules from `heuristic_rules.json`.

A rule can add a small bonus if:

- a specific keyword appears in the input header, and
- the candidate term contains a matching keyword or is listed as an exact target term.

Example: a header containing `image` can receive a bonus for image-related ABCD terms.

### Profile Boost

The profile boost uses the actual column values, not only the header name.

Each column is evaluated against profiling rules from `profiling_rules.json`, such as:

- numeric coordinate ranges,
- date formats,
- URL patterns,
- country names,
- scientific name patterns,
- free-text characteristics.

If a candidate ABCD term is listed as a target for a matching profiling rule, the corresponding profile score is converted into a bounded boost.

```text
profile_boost = best_matching_profile_score * profile_max_boost
```

## Confidence Score

The confidence score estimates how reliable the top-ranked prediction is.

It combines three components:

1. **Margin component**
   - Based on the score difference between the best and second-best candidate.
   - A larger margin means the prediction is less ambiguous.

2. **Semantic component**
   - Based on the semantic score of the best candidate.
   - Semantic scores below `0.70` are treated as weak evidence.

3. **Support component**
   - Adds support if other signals also point to the same candidate.
   - Supporting signals include strong string matches, profile boosts, and heuristic bonuses.

The confidence score is calculated as:

```text
confidence =
    0.55 * margin_component
  + 0.30 * semantic_component
  + 0.15 * support_component
```

The result is capped at `1.0`.

## Manual Review Flag

A prediction is flagged for manual review if at least one review reason exists.

Current review reasons are:

- `small_margin`: the difference between the best and second-best candidate is below `0.04`
- `low_confidence`: the confidence score is below `0.40`

This means a mapping can be flagged either because it is ambiguous or because the overall evidence is too weak.

## Package Structure

### `pipeline.py`
Coordinates the complete mapping workflow and combines all matching strategies into a final ranking.

### `semantic_matching.py`
Generates sentence embeddings for headers and candidate surface forms and computes semantic similarity scores.

### `string_matching.py`
Provides text normalization and fuzzy string similarity functions.

### `heuristic_matching.py`
Applies rule-based score bonuses based on predefined keyword mappings.

### `profiling.py`
Evaluates column contents using configurable profiling rules and generates profiling-based score boosts.

### `confidence.py`
Computes confidence scores for mapping predictions and determines whether manual review is recommended.

## Configuration

The matching pipeline relies on configuration files in `app/config/`.

- `profiling_rules.json` defines value-based profiling rules.
- `profiling_targets.json` maps profiling rules to ABCD terms and provides additional surface forms.
- `heuristic_rules.json` contains manually defined keyword-based rules.
- `weights.json` stores default score weights.


## Quantitative Performance Results

The pipeline was evaluated on 23 annotated column names from `Belege_aus_D.csv`,
comparing `predicted_term` (rank = 1) against the ground truth from
`Ground_Truth.docx`, including accepted alternatives.

### Retrieval Accuracy

| k  | Top-k Accuracy |
|----|----------------|
| 1  | 56.5%          |
| 3  | 82.6%          |
| 5  | 87.0%          |
| 10 | 87.0%          |

### Classification Metrics (Top-1)

| Metric              | Value  |
|---------------------|--------|
| True Positives (TP) | 13     |
| False Positives (FP)| 10     |
| False Negatives (FN)| 10     |
| Precision           | 0.5652 |
| Recall              | 0.5652 |
| F1-Score            | 0.5652 |

### Additional Insights

| Metric                           | Value  |
|----------------------------------|--------|
| Mean rank of correct term        | 1.70   |
| Manual review rate (rank = 1)    | 52.2%  |
| Mean confidence (correct preds)  | 0.6862 |
| Mean confidence (wrong preds)    | 0.3675 |

### Per-Column Results

| Header              | Predicted          | Correct            | Status | Note                    |
|---------------------|--------------------|--------------------|--------|-------------------------|
| HerbariumID         | HerbariumUnit      | UnitID             | ✗      | found at rank 2         |
| Bild                | Image              | FileURL            | ✓      | via alternative         |
| DB                  | SequenceDatabase   | SourceID           | ✗      | found at rank 3         |
| Family              | FileURL            | HigherTaxonName    | ✗      | found at rank 5         |
| FullNameCache       | FullScientificName | FullScientificName | ✓      |                         |
| Anmerkungen         | Notes              | Notes              | ✓      |                         |
| Sammlerteam         | CollectorName      | GatheringAgentsText| ✓      | via alternative         |
| Sammelnummer        | FieldNumber        | FieldNumber        | ✓      |                         |
| CollectionDateBegin | hasDate            | Date               | ✗      | found at rank 3         |
| CollectionDateEnd   | hasDate            | Date               | ✗      | found at rank 3         |
| Country             | hasCountry         | Country            | ✗      | found at rank 2         |
| Locality            | LocalityText       | LocalityText       | ✓      |                         |
| TitelEtikett        | FullScientificName | MarkText           | ✗      | found at rank 3         |
| Expeditionsangabe   | Project            | Project            | ✓      |                         |
| ShowOnMap           | hasCoordinates     | CoordinatesLatLong | ✗      | not found in top-10     |
| Latitude            | LatitudeDecimal    | LatitudeDecimal    | ✓      |                         |
| Longitude           | LongitudeDecimal   | LongitudeDecimal   | ✓      |                         |
| FundortUNdOeko      | Biotope            | Biotope            | ✓      |                         |
| NameCache           | Name               | ScientificName     | ✗      | not found in top-10     |
| Genus               | GenusOrMonomial    | GenusOrMonomial    | ✓      |                         |
| Identifier          | ID                 | Identifier         | ✓      | via alternative         |
| Barcode             | ID                 | UnitID             | ✗      | not found in top-10     |
| StableURI           | ResourceURI        | ResourceURI        | ✓      |                         |

### Interpretation

The pipeline achieves **56.5% Top-1 Accuracy** and **87.0% Top-5 Accuracy**
on the current gold mapping. Several patterns are visible in the failures:

- **`has`-prefix terms** (`hasDate`, `hasCountry`, `hasCoordinates`) appear as
  top-1 predictions for several columns. These are not valid ABCD terms in the
  ground truth and suggest that the synonym JSON still contains non-standard
  term forms that compete with the correct ones.

- **3 columns not found in top-10** (`ShowOnMap`, `NameCache`, `Barcode`) —
  these are the most critical failures, as even increasing k would not help.

- **Confidence is a useful signal**: mean confidence for correct predictions
  (0.69) is notably higher than for wrong predictions (0.37), confirming that
  the confidence score has genuine discriminative value.

- **Manual review rate dropped to 52.2%** compared to the previous run (82.6%),
  suggesting the pipeline is now more confident overall.

- **The test set remains small** (23 entries from a single dataset). These
  results should be treated as indicative rather than conclusive. Evaluation on
  column names from additional data providers is needed to assess generalisation.

---
