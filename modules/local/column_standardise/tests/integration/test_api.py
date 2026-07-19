import pytest
from fastapi.testclient import TestClient
from app.api import app
from unittest.mock import patch
import uuid


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "pipeline_ready" in data
    assert "version" in data
    assert "error" in data


def test_sync_abcd_missing_header(client):
    # If no header is provided, it should fail with 422 Unprocessable Entity
    response = client.post("/sync/abcd")
    assert response.status_code == 422
    assert "abcd-api-key" in response.text.lower()


# Note: We won't test successful sync to avoid external API calls during normal test runs.
# Alternatively, it could be mocked.


def test_standardize_missing_file(client):
    response = client.post("/standardize")
    assert response.status_code == 422


def test_standardize_wrong_file_type(client):
    response = client.post(
        "/standardize", files={"file": ("test.txt", b"dummy content", "text/plain")}
    )
    assert response.status_code == 400
    assert "Only CSV files are supported" in response.text


def test_standardize_invalid_csv_format(client):
    response = client.post(
        "/standardize", files={"file": ("test.csv", b"", "text/csv")}
    )
    assert response.status_code == 400
    assert "Invalid CSV file" in response.text


def test_standardize_empty_csv(client):
    # A CSV with headers but no data will pass pd.read_csv but be df.empty
    response = client.post(
        "/standardize", files={"file": ("test.csv", b"header1,header2\n", "text/csv")}
    )
    assert response.status_code == 400
    assert "CSV file is empty" in response.text


def test_config_synonym_missing_fields(client):
    response = client.post("/config/synonym", json={"target": "something"})
    # Pydantic raises 422 if 'synonym' key is missing completely
    assert response.status_code == 422


def test_config_synonym_empty_fields(client):
    response = client.post("/config/synonym", json={"target": "", "synonym": ""})
    # Method explicitly raises 400 if fields are empty strings
    assert response.status_code == 400
    assert "Target and synonym must be provided" in response.text


def test_config_synonym_invalid_target(client):
    response = client.post(
        "/config/synonym", json={"target": "non_existent_target", "synonym": "test"}
    )
    # Since target doesn't exist, it should return 400
    assert response.status_code == 400
    assert "does not exist" in response.text


def test_standardize_happy_path(client):
    csv_content = b"Latitude,Longitude\n1.0,2.0\n"
    response = client.post(
        "/standardize", files={"file": ("test.csv", csv_content, "text/csv")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "mapping" in data
    assert "metadata" in data
    assert isinstance(data["mapping"], list)
    assert len(data["mapping"]) == 2
    lat_meta = next(m for m in data["mapping"] if m["header"] == "Latitude")
    assert lat_meta["predicted_header"].lower() in [
        "latitudedecimal",
        "latitude decimal",
        "latitude",
    ]


@pytest.mark.parametrize("delimiter", [",", ";", "\t"])
def test_standardize_different_delimiters(client, delimiter):
    # Construct a CSV-like byte string with the specific delimiter
    csv_str = f"Latitude{delimiter}Longitude\n1.0{delimiter}2.0\n"
    csv_content = csv_str.encode("utf-8")

    response = client.post(
        "/standardize", files={"file": ("test.csv", csv_content, "text/csv")}
    )

    # Assert that the parser correctly sniffed the delimiter and didn't crash
    assert response.status_code == 200
    data = response.json()

    # It should correctly identify 2 distinct columns regardless of delimiter
    assert len(data["mapping"]) == 2

    # It should successfully extract 'Latitude' as a distinct header
    headers = [m["header"] for m in data["mapping"]]
    assert "Latitude" in headers


def test_standardize_custom_weights(client):
    csv_content = b"Latitude,Longitude\n1.0,2.0\n"
    response = client.post(
        "/standardize",
        files={"file": ("test.csv", csv_content, "text/csv")},
        data={"semantic_weight": "0.0", "heuristic_weight": "1.0"},
    )
    assert response.status_code == 200


@patch("app.api.sync_abcd_json")
def test_sync_abcd_happy_path(mock_sync, client):
    response = client.post("/sync/abcd", headers={"abcd-api-key": "fake_key"})
    assert response.status_code == 200
    assert "success" in response.json().get("status", "")
    mock_sync.assert_called_once_with(api_key="fake_key")


@pytest.fixture
def clean_profiling_targets():
    path = "app/config/profiling_targets.json"
    with open(path, "r", encoding="utf-8") as f:
        backup = f.read()
    yield
    with open(path, "w", encoding="utf-8") as f:
        f.write(backup)


def test_config_synonym_happy_path(client, clean_profiling_targets):
    unique_synonym = f"Lat_Test_Integration_{uuid.uuid4()}"
    response = client.post(
        "/config/synonym", json={"target": "LatitudeDecimal", "synonym": unique_synonym}
    )
    assert response.status_code == 200
    # Duplicate should fail with 400
    response2 = client.post(
        "/config/synonym", json={"target": "latitude", "synonym": unique_synonym}
    )
    assert response2.status_code == 400
