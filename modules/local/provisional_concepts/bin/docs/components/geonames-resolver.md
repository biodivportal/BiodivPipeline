# GeoNames Locality Resolver

The GeoNames locality resolver resolves place names extracted from unresolved locality and habitat fields (Locality and FundortUNdOeko) against the GeoNames geographical database, returning standardized URIs for geographic entities.

## Overview and purpose

Although the BiodivPortal annotator (WP2) lists GEONAMES among supported vocabularies, it does not actually perform matches against the GeoNames database. This resolver was created as a direct replacement to handle complex German botanical locality text, such as:

"Koenigsberg i. Franken. trockene Bergwiese an der Unfinder Steig, Keuperletten, ca. 350 m"

The component separates geographic place names from ecological, geological, and habitat descriptions. It resolves the place names against GeoNames and passes the remaining habitat text downstream for ENVO matching.

## Resolution workflow

The resolver processes each locality string through a multi-step pipeline:

| Step | Action | Description |
|---|---|---|
| 1. Split | Chunking | Splits locality strings using semicolons, commas, colons, slashes, and spaced dashes. |
| 2. Full chunk search | Exact phrase match | Searches each chunk as a complete phrase first, handling multi-word names like Thür. Wald or Bad Kösen. |
| 3. Word-by-word fallback | Token search | If the full chunk fails, searches each capitalized word individually, skipping lowercase German adjectives and prepositions. |
| 4. Validation | Name checking | Requires the query term to appear in the GeoNames primary name, ASCII name, or alternate names list to prevent spurious fuzzy matches. |
| 5. Feature filtering | Class restriction | Restricts matches to valid geographic feature classes: cities (P), administrative regions (A), terrain features (T), and land areas (L). Non-geographic entities such as hotels and farms are excluded. |
| 6. Preference selection | Ranking | Prefers cities over regions and terrain features, selecting higher population counts within the same feature class. |

### Umlaut normalization

German herbarium records often use ASCII transliterations of umlauts (for example, Koenigsberg instead of Königsberg). The resolver normalizes both input queries and dataset records before comparison:
- ö becomes oe
- ü becomes ue
- ä becomes ae
- ß becomes ss

This normalization allows strings like Koenigsberg to match Königsberg in Bayern accurately.

### Local dataset and caching

Early prototypes used the live GeoNames REST API, but the free tier rate limit of 1,000 requests per hour was insufficient for datasets containing tens of thousands of rows. 

The resolver ships with a local copy of the GeoNames Germany dataset (`DE.txt`, containing approximately 218,000 records). Lookups use an in-memory index that executes exact matching first, substring matching second, and rapidfuzz string comparison as a fallback. Results are cached in memory so that repeated place names (such as Bayern) are evaluated only once.

## Python code interface

You can call `filter_placenames` directly in Python:

```python
from resolvers.locality.place_filter import filter_placenames

field_short, locations = filter_placenames(
    "Koenigsberg i. Franken. trockene Bergwiese",
    country_name="Germany"
)
```

Returned structure:
- `locations`: Dictionary of resolved place names containing standardized GeoNames URIs, feature classes, country codes, and coordinates.
- `field_short`: Remaining text after removing geographic place names, which is passed on to ENVO habitat matching.

Example result dictionary:

```python
locations = {
    "Koenigsberg": {
        "name": "Königsberg in Bayern",
        "uri": "https://sws.geonames.org/2885916/",
        "feature_class": "P",
        "country_code": "DE"
    }
}
field_short = "trockene Bergwiese an der Unfinder Steig"
```

## Performance measurements

Evaluated on German locality text using the local `DE.txt` dataset:

| Dataset size | Resolved records | Resolution accuracy | Execution time |
|---|---|---|---|
| 1,000 rows | 964 | 96.4% | ~93 seconds |
| 5,000 rows | 4,874 | 97.5% | ~8 minutes |
| 10,000 rows | 9,738 | 97.4% | ~21 minutes |
| 20,000 rows | 19,464 | 97.3% | ~57 minutes |

Resolution accuracy remains consistent at around 97.4% as dataset size grows. Adding a substring pre-pass before rapidfuzz reduced per-100-row processing time from 73 seconds down to 9.5 seconds.

## Related documentation

- [LLM splitter](llm-splitter.md): Extracts location fields for GeoNames processing.
- [ENVO matcher](envo-matcher.md): Receives the remaining `field_short` habitat description.
- [Evaluation and performance](../research/evaluation.md): Complete evaluation metrics.
- [Decisions and lessons](../research/decisions.md): Analysis of offline dataset choices.
