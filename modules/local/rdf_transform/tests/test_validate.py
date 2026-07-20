"""Tests for the /validate endpoint and its building blocks.

Layered:
- ontology_loader against the real ontologies in ontologies/
- model_validator on synthetic + real RML inputs
- POST /validate end-to-end through TestClient
"""
from __future__ import annotations

import pytest

from src.core.model_validator import validate_model
from src.core.ontology_loader import LoadedOntologies, load_ontologies_from_dir
from tests.conftest import EXAMPLES, ONTOLOGIES

RML_MAPPING = EXAMPLES / "plant_height_vegetative_raw-model_oboe.rml.ttl"


@pytest.fixture(scope="module")
def real_ontologies() -> LoadedOntologies:
    return load_ontologies_from_dir(ONTOLOGIES)


@pytest.fixture
def real_mapping_bytes() -> bytes:
    return RML_MAPPING.read_bytes()


# ─── ontology_loader ─────────────────────────────────────────────────────

def test_loader_picks_up_oboe(real_ontologies):
    assert "oboe.owl" in real_ontologies.sources
    assert "http://ecoinformatics.org/oboe/oboe.1.2/oboe-core.owl#" in real_ontologies.namespaces
    assert "http://ecoinformatics.org/oboe/oboe.1.2/oboe-core.owl#Observation" in real_ontologies.defined


def test_loader_picks_up_darwin_core(real_ontologies):
    assert "darwin-core.ttl" in real_ontologies.sources
    assert "http://rs.tdwg.org/dwc/terms/" in real_ontologies.namespaces
    # a DwC class (rdfs:Class) and a DwC property (rdf:Property) are indexed
    assert "http://rs.tdwg.org/dwc/terms/Occurrence" in real_ontologies.defined
    assert "http://rs.tdwg.org/dwc/terms/scientificName" in real_ontologies.defined


def test_loader_picks_up_abcd(real_ontologies):
    assert "abcd_concepts.owl" in real_ontologies.sources
    assert "http://rs.tdwg.org/abcd/terms/" in real_ontologies.namespaces
    assert "http://rs.tdwg.org/abcd/terms/Accession" in real_ontologies.defined


def test_loader_returns_empty_for_missing_dir(tmp_path):
    loaded = load_ontologies_from_dir(tmp_path / "does-not-exist")
    assert loaded.is_empty
    assert loaded.sources == ()


def test_loader_filters_non_ontology_files(tmp_path):
    (tmp_path / "README.md").write_text("not an ontology")
    (tmp_path / "notes.txt").write_text("also not")
    loaded = load_ontologies_from_dir(tmp_path)
    assert loaded.is_empty


# ─── model_validator: L1 / L2 / L3 ───────────────────────────────────────

def test_validator_accepts_real_rml_mapping(real_ontologies, real_mapping_bytes):
    result = validate_model(real_mapping_bytes, real_ontologies)
    assert result.valid, result.issues
    assert result.issues == []


def test_validator_flags_broken_turtle(real_ontologies):
    result = validate_model(b"@prefix this is broken", real_ontologies)
    assert not result.valid
    assert any("[L1]" in i for i in result.issues)


def test_validator_flags_non_rml_turtle(real_ontologies):
    """Valid Turtle, but not an RML mapping (no subjectMap / logical source)."""
    result = validate_model(
        b"@prefix ex: <http://example.org/> .\nex:s ex:p ex:o .",
        real_ontologies,
    )
    assert not result.valid
    assert any("[L2]" in i and "rml:subjectMap" in i for i in result.issues)


def test_validator_flags_oboe_typo(real_ontologies, real_mapping_bytes):
    """A typo in an OBOE class name must surface as an [L3] issue."""
    bad = real_mapping_bytes.replace(
        b"oboe:MeasuredValue",
        b"oboe:MeasuredValeu",
    )
    result = validate_model(bad, real_ontologies)
    assert not result.valid
    l3 = [i for i in result.issues if i.startswith("[L3]")]
    assert l3, result.issues
    assert any("MeasuredValeu" in i for i in l3)


# A minimal RML mapping that references Darwin Core terms (a class + a
# property) — used to prove L3 now validates against the DwC namespace too.
_DWC_MAPPING = b"""
@prefix rml: <http://w3id.org/rml/> .
@prefix dwc: <http://rs.tdwg.org/dwc/terms/> .
<#TM> a rml:TriplesMap ;
    rml:logicalSource [ rml:source "d.csv" ; rml:referenceFormulation rml:CSV ] ;
    rml:subjectMap [ rml:template "http://example.org/{id}" ; rml:class dwc:Occurrence ] ;
    rml:predicateObjectMap [ rml:predicate dwc:scientificName ;
                             rml:objectMap [ rml:reference "name" ] ] .
"""


def test_validator_accepts_valid_dwc_terms(real_ontologies):
    result = validate_model(_DWC_MAPPING, real_ontologies)
    assert result.valid, result.issues


def test_validator_flags_dwc_typo(real_ontologies):
    """A typo in a Darwin Core term must surface as an [L3] issue."""
    bad = _DWC_MAPPING.replace(b"dwc:Occurrence", b"dwc:Occrrence")
    result = validate_model(bad, real_ontologies)
    assert not result.valid
    l3 = [i for i in result.issues if i.startswith("[L3]")]
    assert any("Occrrence" in i for i in l3), result.issues


def test_validator_warns_when_no_ontologies_loaded(real_mapping_bytes):
    """If the operator forgot to mount ontologies, L3 should surface a clear
    info message rather than silently passing the mapping."""
    empty = LoadedOntologies()
    result = validate_model(real_mapping_bytes, empty)
    assert not result.valid  # the info note still flips valid → false
    assert any("[L3]" in i and "No ontologies are loaded" in i for i in result.issues)


# ─── route smoke: POST /validate end-to-end ──────────────────────────────

def test_validate_route_returns_valid_for_real_mapping(client, real_mapping_bytes):
    response = client.post(
        "/validate",
        files={"mapping_schema": ("model.rml.ttl", real_mapping_bytes, "text/turtle")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["issues"] == []


def test_validate_route_surfaces_l1_error_for_broken_turtle(client):
    response = client.post(
        "/validate",
        files={"mapping_schema": ("m.ttl", b"@prefix nope", "text/turtle")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert any("[L1]" in i for i in body["issues"])


def test_health_lists_loaded_ontologies(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    # In the test harness the lifespan runs against the real ontologies/
    # dir, so OBOE must appear.
    assert "oboe.owl" in body["ontologies"]
