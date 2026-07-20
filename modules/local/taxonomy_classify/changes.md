# Changelog

### [v.0.2]
- Added Ollama support as an alternative to OpenAI (`use_ollama` query parameter)
- Switched classifier service from a one-shot script to a FastAPI server
- Added `--reload` for reloading the classifier service during development

### [v.0.3]
- Added session caching
- Merged services
- Added CLI support

### [v0.4]
- Output now returns the **whole input dataset** with the land-cover (`llm_*`) and taxonomy (`taxon_*`) columns appended (left-joined on the record id), instead of only the per-record result columns.
- Cultivated rows are **preserved in the output** with empty land-cover/taxonomy fields, rather than dropped. (They are still skipped during classification.)
- Applies to both the batch CLI and the FastAPI `/classify` endpoint.