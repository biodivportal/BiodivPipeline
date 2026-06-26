# Running test without an OpenAI key (Ollama, test-only)

Ollama is used **only for local testing**, never in the pipeline (final product assumes OpenAI). This swaps the LLM backend so the module can be exercised offline.

1. Force Ollama path: set `use_ollama = True` at the top of `process_csv` in `pipeline.py` (do not commit this)

2. One-time Ollama setup:
```bash
   docker network create biodiv
   docker run -d --name ollama --network biodiv -p 11434:11434 ollama/ollama
   sleep 2                                   # let the server come up
   docker exec ollama ollama pull llama3.2   # ~2 GB; warm-up calls llama3.2
```

3. Attach task container to the same network -> add to `tests/nextflow.config`:
```nf
docker.runOptions = '--network biodiv'
```

4. Nextflow might require a `secret 'OPENAI_API_KEY'` even when it is not actually used. If there is a secret error, register a dummy: `nextflow secrets set OPENAI_API_KEY "unused"`.

5. Now regular test commands can be used (ex. `nf-test test modules/local/taxonomy_classify/tests/main.nf.test`).

Ollama can later be removed: `docker rm -f ollama && docker network rm biodiv`

Performance varies a lot as it runs on CPU or RAM (my laptop took 613.659s vs ~20s with OpenAI).