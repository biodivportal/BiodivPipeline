"""Validate an RML mapping against the loaded ontologies.

Three checks, layered from cheap to substantive:

  L1 — RDF syntactic validity (`rdflib.Graph().parse()` succeeds for the
       declared serialization — Turtle or JSON-LD).
  L2 — RML structural sanity (the file declares at least one triples map:
       a `rml:subjectMap` plus a logical source). Rules out random RDF
       uploads. Accepts both the modern RML (w3id) and legacy RML (mmlab)
       / R2RML (rr) vocabularies.
  L3 — ontology-term alignment: every IRI the mapping references in a
       namespace owned by a loaded ontology must be a term declared by
       that ontology. Flags typos and references to renamed / removed
       upstream classes.

L1 and L2 failures set `valid=false` and short-circuit further checks
(no point doing alignment on a file we can't parse). L3 findings also
set `valid=false` so a single boolean answers "should I run /transform
against this mapping?".
"""
from __future__ import annotations

from dataclasses import dataclass, field

from rdflib import Graph, URIRef

from src.core.ontology_loader import LoadedOntologies, term_namespace

# A triples map is identified structurally by a subject map + a logical
# source. We accept all three vocabularies a Schema Editor might emit:
# modern RML (w3id), legacy RML (mmlab) and R2RML (rr).
_SUBJECT_MAP_PREDICATES = (
    URIRef("http://w3id.org/rml/subjectMap"),
    URIRef("http://semweb.mmlab.be/ns/rml#subjectMap"),
    URIRef("http://www.w3.org/ns/r2rml#subjectMap"),
)
_LOGICAL_SOURCE_PREDICATES = (
    URIRef("http://w3id.org/rml/logicalSource"),
    URIRef("http://w3id.org/rml/source"),
    URIRef("http://semweb.mmlab.be/ns/rml#logicalSource"),
    URIRef("http://semweb.mmlab.be/ns/rml#source"),
    URIRef("http://www.w3.org/ns/r2rml#logicalTable"),
)


@dataclass
class ValidationResult:
    valid: bool
    issues: list[str] = field(default_factory=list)


def validate_model(
    model_bytes: bytes,
    ontologies: LoadedOntologies,
    mapping_format: str = "turtle",
) -> ValidationResult:
    """Run L1+L2+L3 over `model_bytes` and return a structured result.

    `mapping_format` is the rdflib parse format ("turtle" or "json-ld").
    """
    # L1 — RDF parse.
    graph = Graph()
    try:
        graph.parse(data=model_bytes, format=mapping_format)
    except Exception as exc:
        return ValidationResult(
            valid=False,
            issues=[f"[L1] {mapping_format} parse failed: {exc}"],
        )

    issues: list[str] = []

    # L2 — RML structural sanity. A usable mapping needs at least one
    # subject map and at least one logical source declaration.
    has_subject_map = any(
        any(graph.subject_objects(p)) for p in _SUBJECT_MAP_PREDICATES
    )
    has_logical_source = any(
        any(graph.subject_objects(p)) for p in _LOGICAL_SOURCE_PREDICATES
    )
    if not has_subject_map:
        issues.append(
            "[L2] No `rml:subjectMap` found — this does not look like an "
            "RML mapping."
        )
    if not has_logical_source:
        issues.append(
            "[L2] No logical source (`rml:logicalSource`/`rml:source`) found "
            "— the mapping declares no data source to bind."
        )

    # If it isn't an RML mapping at all, L3 alignment won't yield anything
    # useful — bail.
    if not has_subject_map:
        return ValidationResult(valid=False, issues=issues)

    # L3 — ontology-term alignment. Walk every IRI referenced by the
    # model. For each IRI whose namespace is owned by a loaded ontology,
    # check it's declared there.
    if ontologies.is_empty:
        issues.append(
            "[L3] No ontologies are loaded; skipping ontology-alignment check. "
            "Set ONTOLOGIES_DIR or drop .owl files into the configured "
            "directory to enable L3."
        )
        return ValidationResult(valid=not issues, issues=issues)

    unknown: list[str] = []
    seen: set[str] = set()
    for triple in graph:
        for node in triple:
            if not isinstance(node, URIRef):
                continue
            iri = str(node)
            if iri in seen:
                continue
            seen.add(iri)
            ns = term_namespace(iri)
            if ns is None or ns not in ontologies.namespaces:
                continue
            if iri not in ontologies.defined:
                unknown.append(iri)

    for iri in sorted(unknown):
        issues.append(
            f"[L3] `{iri}` is referenced but not declared by any loaded "
            f"ontology (namespace {term_namespace(iri)} is owned by "
            f"{', '.join(sorted(ontologies.sources))})."
        )

    return ValidationResult(valid=not issues, issues=issues)
