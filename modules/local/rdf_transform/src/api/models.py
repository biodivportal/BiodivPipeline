"""Pydantic response schemas for the RDF transform API (see routes.py)."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    ontologies: list[str]


class SchemasResponse(BaseModel):
    formats: list[str]


class ValidateResponse(BaseModel):
    valid: bool
    issues: list[str]
