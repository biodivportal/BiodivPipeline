# Decisions and Lessons Learned

This document discusses the design choices, architectural decisions, and technical challenges encountered during the development of WP5. For detailed numerical benchmarks, refer to the [ENVO matcher research](envo-matcher-study.md).

## Plant taxon resolution

Because many of the unresolved plant taxa were due to spelling mismatches and reclassifications 
of specimens we used the GBIF backbone to find the accepted terms and built a rank and 
classification parser to properly match the specimen.

Our solution is incomplete though, after exchanges with the client we redirected
our efforts mostly on ENVO matching and dropped the final resolution against NCBITaxon.
To read more about the implementation of the plant taxon resolution see the [plant taxa doc](../components/plant-taxa.md).

## ENVO matching

Early in the project, we decided against using LLMs in an effort to provide
deterministic results with confidence scores based on classic NLP techniques.
We worked towards parsing the locality strings first to separate place names, environment descriptions and other non relevant terms.

We tested many approaches with our best non-LLM results achieved using rule-based parsing,
though we never got the extraction of the environment descriptions to be good enough
for use in the project.

The local GEONAMES resolution was done in an effort to exclude place names during the parsing step, we left it in the final code base though it doesn't contribute to output.

Our approach for matching the dataset environment descriptors against the ENVO was to use sentence embeddings, similarity measures followed by a reranker model to provide top guesses of matching terms. Though our results were good we couldn't find a combination of techniques that would provide a clear cut-off to decide whether no matching term existed in ENVO. 


### Using an LLM for locality splitting

Despite latency and financial costs, an LLM proved necessary for parsing German locality text. We attempted rule-based regex parsers, named entity recognition, spaCy, GLiNER, and German sentence embeddings like SauerkrautLM.

None of the non-LLM methods handled messy botanical text reliably. German locality fields often contain compound nouns, abbreviations, mixed languages, and Latin names without grammatical structure. The LLM splitter was the only approach that consistently separated geographic place names from habitat descriptions.

### Offline local GeoNames dataset

The public GeoNames REST API enforces a rate limit of 1,000 requests per hour, which is insufficient for dataset processing running into tens of thousands of rows. We bundled a local German dataset (`DE.txt`, roughly 218,000 records) to resolve place names offline, eliminating network dependencies and API throttling.

### English translation prior to ENVO matching

Matching German habitat phrases against the English ENVO ontology worked better after translating the input phrase to English first, rather than querying multilingual sentence embeddings directly. Combining translation into the LLM splitter call avoided extra API roundtrips.

### Label-only bi-encoder indexing

Initially, term synonyms were concatenated into the bi-encoder embedding text. For terms with numerous synonyms, vector averaging diluted the core label embedding. For example, `lake` (which has over a dozen synonyms) dropped to rank 57, causing input phrases to trigger new concept registration instead of matching existing terms. Indexing labels alone restored `lake` to top rank and improved retrieval precision overall.

### Proposal generation without automated registration

Following feedback from client representatives, provisional concepts are proposed with definitions but are not automatically posted to the live portal database. Human curators retain final control over concept registration.

## Key engineering challenges

- Concept identity vs semantic similarity: Vector similarity surfaces related terms effectively, but cannot easily determine whether two short phrases denote the exact same concept. Distinguishing habitat types from physical substrates (for example, pasture versus pasture soil) required adding an LLM identity judge.
- Ground truth limitations: Initial in-house ground truth datasets contained exclusively REGISTER labels, making precision and false-positive evaluation difficult. We relied on the OAEI ENVO to SWEET benchmark set for quantitative retrieval testing.
- Docker image synchronization: Because WP5 runs in containerized environments, host source edits required rebuilding container images before changes took effect, causing initial confusion during local testing.
- Documentation maintenance: Keeping documentation in sync with evolving schema formats required continuous updates, particularly regarding export column definitions.

## Related documentation

- [ENVO matcher study](envo-matcher-study.md): Experimental evaluations and model benchmarks.
- [Evaluation and performance](evaluation.md): Quantitative measurement reports.
- [Requirements compliance](../requirements.md): Project requirements matrix.
