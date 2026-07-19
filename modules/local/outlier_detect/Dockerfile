FROM python:3.11-slim

# PYTHONPATH=/app so the absolute `from app....` imports resolve regardless of
# how the container is invoked (module CLI, `python -m`, or uvicorn).
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

# build-essential + curl are required: hdbscan/cython compile from source, and
# curl backs the HEALTHCHECK below. procps provides `ps` for Nextflow metrics.
RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Keep the `app` package intact at /app/app. The previous `COPY app/ .` flattened
# the package into /app, so `import app` failed at runtime
# (ModuleNotFoundError: No module named 'app').
COPY app/ ./app/

# The Nextflow module invokes `python /app/main_with_cli.py`; expose the package
# entrypoint at that path without duplicating the file.
RUN ln -s app/main_with_cli.py main_with_cli.py

EXPOSE 8000

HEALTHCHECK CMD curl --fail http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]