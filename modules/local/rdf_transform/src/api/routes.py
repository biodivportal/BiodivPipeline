"""HTTP layer of the RDF transform service: defines the FastAPI endpoints
(health, /schemas, /transform, /validate). Validates and normalises incoming
requests, delegates the heavy lifting to src/core (Morph-KGC RML runner, model
validator) and shapes the response. Response schemas live in models.py."""

import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile

from src.api.models import HealthResponse, SchemasResponse, ValidateResponse
from src.core.model_validator import validate_model
from src.core.morph_runner import MorphError, run_morph
from src.core.ontology_loader import LoadedOntologies

router = APIRouter()

_FORMAT_TO_MEDIA = {
    "turtle": "text/turtle",
    "ttl": "text/turtle",
    "nt": "application/n-triples",
    "ntriples": "application/n-triples",
    "jsonld": "application/ld+json",
}

# Morph-KGC hands us an rdflib.Graph; serialize it in the requested format.
_FORMAT_TO_RDFLIB = {
    "turtle": "turtle",
    "ttl": "turtle",
    "nt": "nt",
    "ntriples": "nt",
    "jsonld": "json-ld",
}

# File extension for the Content-Disposition download name, so browsers /
# Swagger save `transform.ttl` rather than a generic `.txt`.
_FORMAT_TO_EXT = {
    "turtle": "ttl",
    "ttl": "ttl",
    "nt": "nt",
    "ntriples": "nt",
    "jsonld": "jsonld",
}


def _detect_mapping_format(filename: Optional[str], override: Optional[str]) -> str:
    """Decide whether the uploaded RML mapping is Turtle or JSON-LD.

    An explicit `mapping_format` form field wins; otherwise infer from the
    filename extension (`.jsonld` / `.json` ⇒ JSON-LD), defaulting to Turtle —
    the format the Schema Editor emits and every RML example uses.
    """
    if override:
        value = override.strip().lower()
        if value in ("turtle", "ttl"):
            return "turtle"
        if value in ("json-ld", "jsonld"):
            return "json-ld"
    suffix = Path(filename or "").suffix.lower()
    if suffix in (".jsonld", ".json"):
        return "json-ld"
    return "turtle"


def get_ontologies(request: Request) -> LoadedOntologies:
    """Pull the LoadedOntologies index attached by main.py's lifespan event.
    Declared as a FastAPI dependency so tests can override it without
    needing a real startup cycle."""
    return request.app.state.ontologies


@router.get("/", response_model=HealthResponse)
def health(ontologies: LoadedOntologies = Depends(get_ontologies)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="0.1.0",
        ontologies=list(ontologies.sources),
    )


@router.get("/schemas", response_model=SchemasResponse)
def list_schema_formats() -> SchemasResponse:
    return SchemasResponse(formats=["rml-turtle", "rml-jsonld"])


@router.post("/transform")
async def transform(
    dataset: UploadFile = File(...),
    mapping_schema: UploadFile = File(...),
    source_type: str = Form("CSV"),
    delimiter: str = Form("COMMA"),
    output_format: str = Form("turtle"),
    # RML mappings are RDF, so the schema may arrive as Turtle or JSON-LD.
    # Auto-detected from the upload's extension; override here if needed.
    mapping_format: Optional[str] = Form(None),
) -> Response:
    fmt = output_format.lower()
    if fmt not in _FORMAT_TO_MEDIA:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported output_format: {output_format!r}. "
                f"Supported: {sorted(set(_FORMAT_TO_MEDIA))}"
            ),
        )

    dataset_bytes = await dataset.read()
    mapping_bytes = await mapping_schema.read()
    map_fmt = _detect_mapping_format(mapping_schema.filename, mapping_format)

    try:
        result = await asyncio.to_thread(
            run_morph,
            dataset_bytes=dataset_bytes,
            mapping_bytes=mapping_bytes,
            source_type=source_type,
            delimiter=delimiter,
            mapping_format=map_fmt,
        )
    except MorphError as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": "RML transformation failed", "error": str(exc)},
        ) from exc

    content = result.graph.serialize(format=_FORMAT_TO_RDFLIB[fmt])

    return Response(
        content=content,
        media_type=_FORMAT_TO_MEDIA[fmt],
        # `inline` (not `attachment`) so Swagger UI still renders the body in
        # the browser; the filename is only used when the user saves it.
        headers={
            "Content-Disposition": f'inline; filename="transform.{_FORMAT_TO_EXT[fmt]}"'
        },
    )


@router.post("/validate", response_model=ValidateResponse)
async def validate(
    mapping_schema: UploadFile = File(...),
    mapping_format: Optional[str] = Form(None),
    ontologies: LoadedOntologies = Depends(get_ontologies),
) -> ValidateResponse:
    """Pre-flight check of an RML mapping:

    - L1 — the file parses as RDF (Turtle or JSON-LD)
    - L2 — the file declares a triples map (`rml:subjectMap` + logical source)
    - L3 — every IRI in a known ontology namespace is actually declared
      there (catches typos and stale mapping references)

    See `src/core/model_validator.py` for the implementation. A clean
    mapping returns `{"valid": true, "issues": []}`; any finding flips
    `valid` to false and lists the specific issues.
    """
    model_bytes = await mapping_schema.read()
    map_fmt = _detect_mapping_format(mapping_schema.filename, mapping_format)
    result = validate_model(model_bytes, ontologies, mapping_format=map_fmt)
    return ValidateResponse(valid=result.valid, issues=result.issues)
