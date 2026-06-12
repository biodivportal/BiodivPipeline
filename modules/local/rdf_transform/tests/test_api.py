"""API-level tests for the FastAPI routes: health, /schemas, /transform's
output-format validation and mapping-format detection, and that /transform
wires the upload through to the Morph-KGC runner correctly."""


def test_health(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_schema_formats(client):
    response = client.get("/schemas")
    assert response.status_code == 200
    formats = response.json()["formats"]
    assert "rml-turtle" in formats
    assert "rml-jsonld" in formats


def test_transform_rejects_unknown_output_format(client):
    response = client.post(
        "/transform",
        files={
            "dataset": ("d.csv", b"a,b\n1,2\n", "text/csv"),
            "mapping_schema": ("m.ttl", b"@prefix ex: <http://example.org/> .", "text/turtle"),
        },
        data={"output_format": "rdfxml"},
    )
    assert response.status_code == 400
    assert "Unsupported output_format" in response.json()["detail"]


def test_detect_mapping_format():
    """Turtle by default; JSON-LD by extension or explicit override."""
    from src.api.routes import _detect_mapping_format

    assert _detect_mapping_format("model.ttl", None) == "turtle"
    assert _detect_mapping_format("model.rml.ttl", None) == "turtle"
    assert _detect_mapping_format(None, None) == "turtle"
    assert _detect_mapping_format("model.jsonld", None) == "json-ld"
    assert _detect_mapping_format("model.json", None) == "json-ld"
    # explicit override wins over the extension
    assert _detect_mapping_format("model.ttl", "json-ld") == "json-ld"
    assert _detect_mapping_format("model.jsonld", "turtle") == "turtle"


def test_transform_passes_upload_through_to_runner(client, monkeypatch):
    """The route must forward the dataset/mapping bytes and the detected
    mapping format to run_morph, and serialize the returned graph."""
    from rdflib import Graph
    captured = {}

    def fake_run_morph(**kwargs):
        captured.update(kwargs)
        from src.core.morph_runner import MorphResult
        g = Graph()
        g.parse(data="@prefix ex: <http://example.org/> . ex:s ex:p ex:o .",
                format="turtle")
        return MorphResult(graph=g, triples=len(g))

    monkeypatch.setattr("src.api.routes.run_morph", fake_run_morph)

    response = client.post(
        "/transform",
        files={
            "dataset": ("d.json", b'[{"a":"1"}]', "application/json"),
            "mapping_schema": ("m.jsonld", b"{}", "application/ld+json"),
        },
        data={"source_type": "JSON", "output_format": "turtle"},
    )

    assert response.status_code == 200, response.text
    assert captured["source_type"] == "JSON"
    assert captured["mapping_format"] == "json-ld"  # detected from .jsonld
    assert captured["dataset_bytes"] == b'[{"a":"1"}]'
    assert "ex:p" in response.text or "http://example.org/p" in response.text
