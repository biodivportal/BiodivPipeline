# syntax=docker/dockerfile:1
#
# WP6 column_standardise — ABCD column standardiser (vendored from
# github.com/erenkcdg/wp6_biodiv). The Nextflow module calls
# `python -m app.standardize` from /app; the standalone FastAPI service is the
# default CMD for independent use.
#
# Semantic matching loads a sentence-transformers model
# (intfloat/multilingual-e5-small) at import time, so it is baked into the image
# for offline, network-free runs. We install the CPU-only torch build to avoid
# the multi-GB CUDA wheels the default index would otherwise resolve.
#
# The container runs under an arbitrary uid (docker.runOptions
# '-u $(id -u):$(id -g)'), so the model cache is made world-readable and
# HOME/caches point at writable /tmp.
FROM python:3.10-slim

# procps provides `ps`, which Nextflow uses to collect resource metrics
# (required because the docker profile runs containers rootless).
RUN apt-get update \
    && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Install the CPU-only build of torch first so sentence-transformers doesn't pull
# the multi-GB CUDA wheels that the default index would resolve.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install the remaining dependencies from requirements.txt.
RUN pip install --no-cache-dir -r requirements.txt

# Bake the embedding model into a world-readable cache so the arbitrary-uid
# runtime process can load it offline.
ENV HF_HOME=/opt/hf \
    SENTENCE_TRANSFORMERS_HOME=/opt/hf
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small')" \
    && chmod -R 0777 /opt/hf

# Force offline model loading at runtime and give the arbitrary-uid process a
# writable HOME (dotenv, HF lock files). USER/LOGNAME are set because the
# container runs under a uid absent from /etc/passwd; getpass.getuser() reads
# these env vars first and would otherwise crash on pwd.getpwuid().
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HOME=/tmp \
    USER=app \
    LOGNAME=app \
    XDG_CACHE_HOME=/tmp/.cache \
    MPLCONFIGDIR=/tmp/mpl \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Source layout must match the module's `python -m app.standardize` invocation:
# the `app` package lives at /app/app and data/abcd.json at /app/data.
COPY app/ ./app/
COPY data/ ./data/

EXPOSE 8000

# Default CMD serves the standalone FastAPI app; the Nextflow module overrides
# this with the batch CLI (`python -m app.standardize`).
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
