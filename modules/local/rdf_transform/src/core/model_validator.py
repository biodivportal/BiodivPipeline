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

from rdflib import Graph, URIRef, Literal

from src.core.ontology_loader import LoadedOntologies, term_namespace

import re

from src.core.morph_runner import (
    MorphError,
    read_tabular_dataset
)

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

#Modern RML reference
# Legacy RML reference
# Legacy R2RML column reference

_COLUMN_REFERENCE_PREDICATES = (
    URIRef("http://w3id.org/rml/reference"),
    URIRef("http://semweb.mmlab.be/ns/rml#reference"),
    URIRef("http://www.w3.org/ns/r2rml#column"),
)

# References embedded inside URI templates.

_TEMPLATE_PREDICATES = (
    URIRef("http://w3id.org/rml/template"),
    URIRef("http://semweb.mmlab.be/ns/rml#template"),
    URIRef("http://www.w3.org/ns/r2rml#template"),
)

_TEMPLATE_VARIABLE_PATTERN = re.compile(r"\{([^{}]+)\}")


@dataclass
class ValidationResult:
    valid: bool
    issues: list[str] = field(default_factory=list)

def extract_column_references(graph: Graph) -> set[str]:
    """
    Extract CSV column references from an RML graph.

    Supports:
    - Modern RML: rml:reference
    - Legacy R2RML: rr:column
    - Modern and legacy template placeholders
    """

    references = set()

    # 1. Direct column references.
    for predicate in _COLUMN_REFERENCE_PREDICATES:
        for value in graph.objects(None, predicate):
            if isinstance(value, Literal):
                references.add(str(value))

    # 2. Column references inside templates.
    for predicate in _TEMPLATE_PREDICATES:
        for value in graph.objects(None, predicate):
            if not isinstance(value, Literal):
                continue

            template = str(value)

            placeholders = _TEMPLATE_VARIABLE_PATTERN.findall(
                template
            )

            references.update(placeholders)

    return references

def validate_model(
    model_bytes: bytes,
    ontologies: LoadedOntologies,
    mapping_format: str = "turtle",
    dataset_bytes: bytes | None = None,
    source_type: str = "CSV",
    delimiter: str = "COMMA",
) -> ValidationResult:
    """Run L1+L2+L3+L4 over `model_bytes` and return a structured result.

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
            "[L3] No ontologies are loaded; "
            "skipping ontology-alignment check."
        )

    else:
        unknown = []
        seen = set()

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
                f"[L3] `{iri}` is referenced but not declared "
                f"by any loaded ontology."
            )


    # L4 — dataset-column compatibility.

    if dataset_bytes is not None:

        # This validation concerns tabular field names.
        # JSON sources require separate JSONPath validation.
        if (source_type or "CSV").upper() != "JSON":

            try:
                dataset_df = read_tabular_dataset(
                    dataset_bytes,
                    delimiter
                )

                dataset_headers = set(
                    str(header)
                    for header in dataset_df.columns
                )

                mapping_references = extract_column_references(
                    graph
                )

                missing_columns = sorted(
                    mapping_references - dataset_headers
                )

                for column in missing_columns:
                    issues.append(
                        f"[L4] Mapping references CSV column "
                        f"{column!r}, but this column does not "
                        f"exist in the supplied dataset."
                    )

            except MorphError as exc:
                issues.append(
                    f"[L4] Could not validate dataset columns: {exc}"
                )


    return ValidationResult(
        valid=not issues,
        issues=issues
    )
