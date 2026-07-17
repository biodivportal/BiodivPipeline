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

# Install the CPU-only build of torch first so we don't pull the multi-GB CUDA
# wheels that the default index would resolve.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Bake the ENVO embedding and reranking models into the image so the locality path needs no
# network download at runtime. Store them in a world-writable location because the
# container runs under an arbitrary uid (docker.runOptions '-u $(id -u):$(id -g)').
ENV HF_HOME=/opt/hf \
    SENTENCE_TRANSFORMERS_HOME=/opt/hf
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer('BAAI/bge-large-en-v1.5'); CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2')" \
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

# Pre-download local GeoNames data for Germany (DE) so it is baked into the image
RUN python clients/local_geonames.py

