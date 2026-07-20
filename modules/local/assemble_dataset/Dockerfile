# syntax=docker/dockerfile:1
#
# WP1 assemble_dataset — standard-library-only dataset assembler. The Nextflow
# module invokes `python /app/bin/assemble_dataset.py`; the script is baked in so
# the task is fully hermetic under the docker profile (no host Python required).
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

# procps provides `ps`, which Nextflow uses to collect resource metrics.
RUN apt-get update \
    && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

# Standard library only — nothing to pip install. Bake the assembler.
COPY bin/ ./bin/

CMD ["python", "/app/bin/assemble_dataset.py", "--help"]
