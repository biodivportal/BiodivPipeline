# WP5 provisional_concepts — provisional concept recommender
# Contains both resolver paths:
#   - taxon  (GBIF, no key)          -> run with --species
#   - locality (ENVO embeddings+LLM) -> run with --localities (needs WP5_OPENAI_API_KEY)
FROM python:3.11-slim

# procps provides `ps`, which Nextflow uses to collect resource metrics
# (required because the docker profile runs containers rootless).
RUN apt-get update \
    && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements.txt first for caching
COPY requirements.txt .

# cpu/gpu builds
# defaults to cpu build
# To use gpu use `docker build --build-arg DEVICE=gpu -t ghcr.io/biodivportal/provisional-concepts:0.2-gpu -f Dockerfile`.
ARG DEVICE="cpu"

RUN if [ "$DEVICE" = "cpu" ]; then \
        pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
        pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu; \
    elif [ "$DEVICE" = "gpu" ]; then \
        pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cu126 && \
        pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu126; \
    else \
        echo "Error: Unsupported DEVICE '$DEVICE'. Must be 'cpu' or 'gpu'." && exit 1; \
    fi

# Bake the ENVO embedding and reranking models into the image so the locality path needs no
# network download at runtime. Store them in a world-writable location because the
# container runs under an arbitrary uid (docker.runOptions '-u $(id -u):$(id -g)').
ENV HF_HOME=/opt/hf \
    SENTENCE_TRANSFORMERS_HOME=/opt/hf
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer('BAAI/bge-large-en-v1.5'); CrossEncoder('BAAI/bge-reranker-v2-m3')" \
    && chmod -R 0777 /opt/hf

# Force offline model loading at runtime and give the arbitrary-uid process a
# writable HOME (pygbif caching, dotenv, HF lock files).
# USER/LOGNAME are set because the container runs under an arbitrary uid that is
# absent from /etc/passwd; torch/getpass.getuser() reads these env vars first and
# would otherwise crash on pwd.getpwuid(). The *_CACHE_DIR vars keep every
# framework writing under the writable HOME.
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HOME=/tmp \
    USER=app \
    LOGNAME=app \
    TORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor \
    MPLCONFIGDIR=/tmp/mpl \
    XDG_CACHE_HOME=/tmp/.cache \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy the WP5 source (main.py, resolvers/, clients/, ontology_config.json, data/)
COPY . /app
RUN mkdir -p /app/geonames_data \
    && chmod -R 0777 /app/geonames_data

# Pull the pre-built ENVO embeddings + whole-ENVO term set from the single-arch
# (linux/amd64) data image that CI builds via Dockerfile.data.
ARG DATA_IMAGE=ghcr.io/biodivportal/provisional-concepts-data:0.4
COPY --from=${DATA_IMAGE} /app/data/envo_embeddings.pkl /app/data/envo_relevant_terms.json /app/data/
RUN chmod -R 0777 /app/data

# Pre-download local GeoNames data for Germany (DE) so it is baked into the image
RUN python clients/local_geonames.py

CMD ["python", "/app/main.py", "--help"]

