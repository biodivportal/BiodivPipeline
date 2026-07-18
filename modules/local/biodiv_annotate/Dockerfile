# syntax=docker/dockerfile:1
#
# WP2 biodiv_annotate — BiodivPortal term-annotation module. The Nextflow module
# invokes `python /app/bin/annotate_biodiv.py`; the script, its ontology config,
# and the recommender are baked in so the task needs nothing from the host.
FROM python:3.11-slim

# The container runs under an arbitrary uid (docker.runOptions
# '-u $(id -u):$(id -g)'), so give the process a writable HOME and set
# USER/LOGNAME (the uid is absent from /etc/passwd).
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/tmp \
    USER=app \
    LOGNAME=app

WORKDIR /app

# procps provides `ps`, which Nextflow uses to collect resource metrics
# (required because the docker profile runs containers rootless).
RUN apt-get update \
    && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

# Runtime deps: HTTP client for the BiodivPortal API + dotenv for local .env use.
RUN pip install --no-cache-dir requests==2.32.3 python-dotenv==1.0.1

# Bake the module's bin/ (annotate script + ontology config + recommender).
COPY bin/ ./bin/

# Default command for standalone use; the Nextflow module overrides it.
CMD ["python", "/app/bin/annotate_biodiv.py", "--help"]
