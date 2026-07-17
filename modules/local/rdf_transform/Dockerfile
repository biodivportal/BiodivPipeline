# syntax=docker/dockerfile:1.7
#
# RDF Matching and Transformation Service — pure-Python runtime.
#
# The transformation engine is Morph-KGC (RML → RDF), a maintained Python
# library; there is no JVM and no Karma JAR to build or trim any more. Build
# with a plain:
#
#   docker build -t rdf-transform .
#
# Morph-KGC needs Python >= 3.10; we pin 3.11.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  ONTOLOGIES_DIR=/app/ontologies

# tini: PID 1 signal handling. procps: provides `ps`, which Nextflow calls to
# collect per-task CPU/memory metrics — the task fails without it under the
# docker profile. curl: used by the nf module script to reach the service's
# HTTP API (health / validate / transform).
RUN apt-get update \
  && apt-get install -y --no-install-recommends tini procps curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Reference ontologies for /validate L3 (alignment check). The loader
# filters by extension, so the README.md sitting alongside is harmless.
# Drop more .owl/.ttl files into ontologies/ to extend coverage.
COPY ontologies /app/ontologies

COPY main.py ./
COPY src ./src

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request, sys; \
  sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3).status == 200 else 1)" \
  || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
