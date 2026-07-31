# ENVO Matcher: Research Study

This document details the experimental research conducted on the ENVO matcher, covering evaluated models, candidate pool strategies, retrieval algorithms, and performance findings.

It is meant as an overview over the experiments we ran, it is not a thorough scientific evaluation and should inform further work.

## The core matching challenge

Matching free-text habitat descriptions to ENVO ontology terms presents distinct semantic challenges. Short phrases such as pasture, roadside soil, or spruce forest often lack grammatical context, making it difficult for vector similarity models to judge concept identity.

Two main error types were observed:
1. False matches to related substrate concepts, such as pasture matching pasture soil, or spruce forest matching spruce forest soil.
2. High-confidence false matches, which incorrectly prevent missing concepts from being proposed for registration.

While semantic retrieval effectively surfaces candidate terms, it requires an identity verification step to confirm whether two terms describe the exact same concept.

## Models evaluated

| Model | Architecture | Role and findings |
|---|---|---|
| `BAAI/bge-large-en-v1.5` | Bi-encoder | Selected bi-encoder model. Produced the strongest similarity score margins on English text. |
| `BAAI/bge-m3` | Multilingual bi-encoder | Tested for direct German matching. Performed worse than translation followed by English bi-encoder matching. |
| `intfloat/multilingual-e5-large` | Bi-encoder | Initial baseline model. Replaced due to query prefix mismatch issues. |
| `cross-encoder/ms-marco-MiniLM-L-12-v2` | Cross-encoder | Initial reranker. Scores compressed into a narrow band (0.00 to 0.03) because it was trained on general web search. |
| `BAAI/bge-reranker-v2-m3` | Cross-encoder | Selected reranker model. Significantly widened score margins after sigmoid calibration. |
| BM25 (Okapi implementation) | Lexical retriever | Evaluated for reciprocal rank fusion. Exacerbated substrate false matches and was discarded. |

Domain-specific models were evaluated but were often restricted to single languages, limiting their utility in mixed German and English processing.

## Candidate pool strategies

We initially attempted to curate the ENVO ontology by restricting the index to a subset of habitat terms (2,189 terms). However, taxonomy irregularities caused this curated pool to miss valid concepts, lowering the recall ceiling significantly.

| Candidate pool | Term count | Recall ceiling | R@1 | R@3 | Clear false matches |
|---|---|---|---|---|---|
| Curated environment slice | 2,189 | 0.51 | 0.37 | 0.46 | 49 |
| Full active ENVO term index | 3,872 | 0.98 | 0.66 | 0.85 | 44 |
| Habitat-only subset | 572 | 0.10 | 0.07 | 0.08 | 3 |

Indexing the full active ENVO term set (3,872 terms) raised the recall ceiling from 0.51 to 0.98. Filtering non-habitat terms was shifted from index pre-filtering to the final LLM decision stage using metadata flags.

## Retrieval techniques tested

- Dense single-vector label-only indexing: Selected. Indexing term labels without concatenated synonyms prevented vector dilution and fixed ranking errors on generic terms like lake.
- BGE query prefix correction: Selected. Applying proper instruction prefixes improved score separation.
- Cross-encoder reranking (`bge-reranker-v2-m3`): Selected. Improved candidate ranking order prior to LLM verification.
- Term definitions in index: Discarded. Including long definitions diluted label embeddings and reduced retrieval precision.
- Late-interaction retrieval (ColBERT token MaxSim via `bge-m3`): Discarded. Latched onto shared keywords (such as soil or water) and increased false matches.
- Lexical-dense fusion (BM25 + Dense RRF): Discarded. Lexical matching reinforced head-word false positives.
- Direct multilingual matching (`bge-m3` on German): Discarded. Performed worse than translating German text to English before dense matching.

Methods that score at token levels (such as ColBERT or token MaxSim) performed well on clean ontology labels but degraded on noisy field text, latching onto individual words. Single dense vector embeddings provided more stable candidate lists.

## Translation approach

Because ENVO is an English ontology and input records are in German, translation is required. We compared automated translation via Google Translate (`deep-translator`) against in-pass LLM translation using the GEMET multilingual environmental thesaurus.

On clean thesaurus terms, both approaches performed comparably. On messy field locality phrases containing German compounds, Latin botanical names, or French loanwords, LLM translation produced significantly more accurate English terms.

## Evaluation datasets

- OAEI ENVO to SWEET (522 pairs): Primary benchmark for retrieval evaluation.
- GEMET: Used to benchmark translation accuracy across German and English parallel terms.
- Internal BGBM sample (38 records): Used for end-to-end testing across split, match, and decision stages.

## Summary of shipped vs discarded approaches

Shipped architecture:
- Full active ENVO index (3,872 terms) with habitat metadata flags.
- Label-only bi-encoder retrieval using `bge-large-en-v1.5`.
- Cross-encoder reranking using `bge-reranker-v2-m3`.
- In-pass LLM translation during locality splitting.
- LLM identity judge evaluating candidate shortlists alongside CLC hints.

Discarded approaches:
- Late-interaction token matching (ColBERT).
- Indexing definitions or concatenated synonym lists.
- Lexical-dense hybrid fusion (BM25 + RRF).
- Direct multilingual embedding search without translation.
- Curated ontology sub-pools.

## Related documentation

- [ENVO matcher component](../components/envo-matcher.md): Implementation details.
- [Evaluation and performance](evaluation.md): Quantitative benchmark summaries.
- [Decisions and lessons](decisions.md): High-level architectural lessons.
