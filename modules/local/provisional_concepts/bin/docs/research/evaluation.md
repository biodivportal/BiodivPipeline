# Evaluation and Performance

This document summarizes the performance measurements, evaluation tools, and benchmark results for WP5.

To evaluate matching performance, we built a dedicated evaluation script (`evaluate.py`) integrated into the main CLI pipeline. The ground truth dataset we put together was AI-generated using structured LLM batching with strict concept-identity prompts, and should be considered correct for evaluation purposes.

## The evaluation script (`evaluate.py`)

The evaluation script measures candidate retrieval precision, recall, top-1 accuracy, top-3 accuracy, and decision disposition accuracy against ground truth datasets.

### How to use it

You can run evaluation standalone using `evaluate.py`:

```bash
python evaluate.py --ground-truth data/provisional_concepts_ground_truth.csv --eval-output data/evaluation_results.json
```

Or run it in-line during pipeline execution via `main.py`:

```bash
python main.py --input unresolved_terms.csv --output provisional_concepts.json \
    --evaluate \
    --ground-truth data/provisional_concepts_ground_truth.csv \
    --eval-output data/evaluation_results.json
```

The script outputs a JSON summary containing:
- Precision, recall, and F1 scores for ENVO matches.
- Top-1 and top-3 retrieval accuracy (how often the true concept appears in rank 1 or the top 3 candidates).
- Disposition accuracy (how accurately the system assigns ACCEPT versus REGISTER).

## GeoNames resolver performance

Evaluated on German locality strings using a local `DE.txt` dump:

| Row count | Resolved records | Resolution accuracy | Execution time |
|---|---|---|---|
| 1,000 | 964 | 96.4% | ~93 seconds |
| 5,000 | 4,874 | 97.5% | ~8 minutes |
| 10,000 | 9,738 | 97.4% | ~21 minutes |
| 20,000 | 19,464 | 97.3% | ~57 minutes |

Accuracy stabilizes around 97.4%, scaling linearly with row count.

## ENVO matcher retrieval accuracy

Evaluated on the OAEI ENVO to SWEET benchmark set (522 concept pairs) comparing candidate pool indexing strategies:

| Metric | Curated pool (2,189 terms) | Full ENVO pool (3,872 terms) |
|---|---|---|
| Recall ceiling | 0.51 | 0.98 |
| Recall at rank 1 | 0.37 | 0.66 |
| Recall at rank 3 | 0.46 | 0.85 |
| Precision at rank 1 (in pool) | 0.72 | 0.67 |

Switching the bi-encoder to a label-only index further improved recall at rank 1 to 0.69 and precision at rank 1 to 0.70, resolving ranking issues on generic terms like lake.

On an end-to-end sample of 38 BGBM herbarium records, the full pipeline (splitting, candidate retrieval, reranking, and LLM judging) yielded:
- ACCEPT: 7 records (matched existing ENVO terms)
- REGISTER: 3 records (valid missing habitat concepts, with generated definitions)
- DISCARD: 16 records (place-name-only strings or non-environmental text)

Though these benchmarks show high retrieval quality, it is worth noting that they represent a best-case scenario. Benchmark sets use clean concept pairs, whereas real-world German field notes often contain shorthand, mixed languages, and ambiguous place names.

Note on legacy metrics: Earlier evaluation reports quoted precision of 0.145 and recall of 0.500. Those figures resulted from an early internal ground truth dataset where all rows were labeled REGISTER, making precision metrics unreliable.

## Plant taxa resolver

GBIF match confidence across sample plant names ranged from 94% to 100% across EXACT, FUZZY, and HIGHERRANK match types. Systematic benchmarking against a dedicated plant taxonomy ground truth was deferred to focus development efforts on the ENVO locality matcher.

## End-to-end pipeline summary

The 38-record sample demonstrates the resolution decision logic in practice: 7 terms were accepted as existing ENVO concepts, 3 were proposed as new concepts with generated definitions, and 16 were correctly discarded as place-only descriptions.

## Evaluation methodology and dataset availability

- OAEI ENVO to SWEET set (522 pairs): Primary benchmark for ENVO retrieval evaluation. The full dataset (`envo-sweet.rdf`, `envo.owl`, and `sweet.owl`) is stored directly in the repository under `bin/experiments/cache/oaei_biodiv/` and is available immediately if clients ask for it.
- GEMET parallel corpus: Multilingual thesaurus used to evaluate translation performance between German and English terms.
- AI-generated ground truth (204 rows): Generated via LLM batching with strict identity prompts and validated for evaluation use.

## Related documentation

- [ENVO matcher research study](envo-matcher-study.md): Comprehensive analysis of models and retrieval methods.
- [Decisions and lessons](decisions.md): Architecture trade-offs and ground-truth discussions.
