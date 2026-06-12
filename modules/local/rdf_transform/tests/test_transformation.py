"""End-to-end: POST /transform with the InfAI sample through Morph-KGC and
compare to the InfAI ground truth. Runs for both the CSV and JSON inputs —
the same RML mapping drives both — and asserts graph isomorphism (same triple
set modulo blank-node identity)."""
import pytest
from rdflib import Graph
from rdflib.compare import to_isomorphic

from tests.conftest import EXAMPLES, requires_morph

MAPPING = EXAMPLES / "plant_height_vegetative_raw-model_oboe.rml.ttl"
GROUND_TRUTH = EXAMPLES / "plant_height_vegetative_raw_germany_20_oboe.ttl"


@requires_morph
@pytest.mark.parametrize(
    "dataset_name, source_type, delimiter",
    [
        ("plant_height_vegetative_raw_germany_20.json", "JSON", "COMMA"),
        ("plant_height_vegetative_raw_germany_20.csv", "CSV", "TAB"),
    ],
)
def test_transform_matches_ground_truth(client, dataset_name, source_type, delimiter):
    dataset = EXAMPLES / dataset_name

    with dataset.open("rb") as ds, MAPPING.open("rb") as mdl:
        response = client.post(
            "/transform",
            files={
                "dataset": (dataset.name, ds, "application/octet-stream"),
                "mapping_schema": (MAPPING.name, mdl, "text/turtle"),
            },
            data={
                "source_type": source_type,
                "delimiter": delimiter,
                "output_format": "turtle",
            },
        )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/turtle")

    got = Graph().parse(data=response.text, format="turtle")
    want = Graph().parse(source=str(GROUND_TRUTH), format="nt")

    assert len(got) == len(want)
    assert to_isomorphic(got) == to_isomorphic(want)


@requires_morph
def test_transform_emits_jsonld(client):
    dataset = EXAMPLES / "plant_height_vegetative_raw_germany_20.json"

    with dataset.open("rb") as ds, MAPPING.open("rb") as mdl:
        response = client.post(
            "/transform",
            files={
                "dataset": (dataset.name, ds, "application/json"),
                "mapping_schema": (MAPPING.name, mdl, "text/turtle"),
            },
            data={"source_type": "JSON", "output_format": "jsonld"},
        )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/ld+json")
    # round-trips back to the same graph as the ground truth
    got = Graph().parse(data=response.text, format="json-ld")
    want = Graph().parse(source=str(GROUND_TRUTH), format="nt")
    assert to_isomorphic(got) == to_isomorphic(want)
