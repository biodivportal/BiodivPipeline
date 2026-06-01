import sys
import os
import csv
import json
import tempfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../bin"))

from annotate_biodiv import (
    normalize_term,
    guess_category,
    remove_duplicates,
    collect_terms,
    save_enriched_csv,
    get_ontology_name,
    simplify_response,
    save_unresolved,
    annotate_term,
    FIELDS_TO_CHECK,
)

# normalize_term

def test_normalize_term_basic():
    assert normalize_term("Hieracium") == "Hieracium"

def test_normalize_term_strips_whitespace():
    assert normalize_term("  Hieracium  ") == "Hieracium"

def test_normalize_term_collapses_spaces():
    assert normalize_term("Hieracium   murorum") == "Hieracium murorum"

def test_normalize_term_empty_string():
    assert normalize_term("") == ""

def test_normalize_term_none():
    assert normalize_term(None) == ""

def test_normalize_term_unicode():
    assert normalize_term("Stra\u00dfe") == "Straße"

def test_normalize_term_special_chars():
    assert normalize_term("Hieracium (L.) Zahn") == "Hieracium (L.) Zahn"

#  guess_category 

def test_guess_category_taxon_fields():
    assert guess_category("FullNameCache") == "taxon"
    assert guess_category("NameCache") == "taxon"
    assert guess_category("Genus") == "taxon"
    assert guess_category("Family") == "taxon"

def test_guess_category_location_fields():
    assert guess_category("Country") == "location"
    assert guess_category("Locality") == "location"

def test_guess_category_ecology():
    assert guess_category("FundortUNdOeko") == "ecology_or_habitat"

def test_guess_category_expedition():
    assert guess_category("TitelEtikett") == "expedition_or_note"
    assert guess_category("Expeditionsangabe") == "expedition_or_note"

def test_guess_category_unknown():
    assert guess_category("SomeRandomField") == "unknown"

def test_guess_category_empty_string():
    assert guess_category("") == "unknown"

#  get_ontology_name 

def test_get_ontology_name_basic():
    assert get_ontology_name("https://data.biodivportal.gfbio.org/ontologies/NCBITAXON") == "NCBITAXON"

def test_get_ontology_name_trailing_slash():
    assert get_ontology_name("https://data.biodivportal.gfbio.org/ontologies/ENVO/") == "ENVO"

def test_get_ontology_name_empty():
    assert get_ontology_name("") == ""

def test_get_ontology_name_none():
    assert get_ontology_name(None) == ""

#  remove_duplicates 

def test_remove_duplicates_removes_exact_duplicates():
    annotations = [
        {"matched_text": "Hieracium", "class_id": "http://x.org/1", "ontology": "NCBITAXON"},
        {"matched_text": "Hieracium", "class_id": "http://x.org/1", "ontology": "NCBITAXON"},
    ]
    result = remove_duplicates(annotations)
    assert len(result) == 1

def test_remove_duplicates_keeps_different_ontologies():
    annotations = [
        {"matched_text": "Hieracium", "class_id": "http://x.org/1", "ontology": "NCBITAXON"},
        {"matched_text": "Hieracium", "class_id": "http://x.org/2", "ontology": "ENVO"},
    ]
    result = remove_duplicates(annotations)
    assert len(result) == 2

def test_remove_duplicates_empty_list():
    assert remove_duplicates([]) == []

def test_remove_duplicates_preserves_order():
    annotations = [
        {"matched_text": "A", "class_id": "http://x.org/1", "ontology": "NCBITAXON"},
        {"matched_text": "B", "class_id": "http://x.org/2", "ontology": "NCBITAXON"},
        {"matched_text": "A", "class_id": "http://x.org/1", "ontology": "NCBITAXON"},
    ]
    result = remove_duplicates(annotations)
    assert result[0]["matched_text"] == "A"
    assert result[1]["matched_text"] == "B"

def test_remove_duplicates_single_item():
    annotations = [
        {"matched_text": "Hieracium", "class_id": "http://x.org/1", "ontology": "NCBITAXON"},
    ]
    result = remove_duplicates(annotations)
    assert len(result) == 1

#  collect_terms 

def make_rows(data):
    return [{"HerbariumID": str(i), **d} for i, d in enumerate(data)]

def test_collect_terms_basic():
    rows = make_rows([{"Genus": "Hieracium", "Family": "ASTERACEAE"}])
    terms = collect_terms(rows)
    assert "Genus::hieracium" in terms

def test_collect_terms_deduplicates():
    rows = make_rows([
        {"Genus": "Hieracium"},
        {"Genus": "Hieracium"},
    ])
    terms = collect_terms(rows)
    genus_keys = [k for k in terms if k.startswith("Genus::")]
    assert len(genus_keys) == 1

def test_collect_terms_tracks_occurrences():
    rows = make_rows([
        {"Genus": "Hieracium"},
        {"Genus": "Hieracium"},
    ])
    terms = collect_terms(rows)
    key = "Genus::hieracium"
    assert len(terms[key]["occurrences"]) == 2

def test_collect_terms_skips_empty_fields():
    rows = make_rows([{"Genus": "", "Family": "ASTERACEAE"}])
    terms = collect_terms(rows)
    assert not any("genus::" in k for k in terms)

def test_collect_terms_multiple_fields():
    rows = make_rows([{"Genus": "Hieracium", "Family": "ASTERACEAE", "Country": "Germany"}])
    terms = collect_terms(rows)
    assert any("Genus" in k for k in terms)
    assert any("Family" in k for k in terms)
    assert any("Country" in k for k in terms)

#  simplify_response 

def test_simplify_response_basic():
    api_result = [{
        "annotatedClass": {
            "@id": "http://purl.obolibrary.org/obo/NCBITaxon_1",
            "links": {
                "ontology": "https://data.biodivportal.gfbio.org/ontologies/NCBITAXON",
                "ui": "https://biodivportal.gfbio.org/ontologies/NCBITAXON?p=classes&conceptid=http://purl.obolibrary.org/obo/NCBITaxon_1"
            }
        },
        "annotations": [{"text": "Hieracium", "matchType": "EXACT", "from": 1, "to": 9}]
    }]
    result = simplify_response(api_result, "Genus")
    assert len(result) == 1
    assert result[0]["matched_text"] == "Hieracium"
    assert result[0]["source_field"] == "Genus"
    assert result[0]["ontology"] == "NCBITAXON"

def test_simplify_response_empty():
    assert simplify_response([], "Genus") == []

def test_simplify_response_suspicious_short_match():
    api_result = [{
        "annotatedClass": {
            "@id": "http://x.org/1",
            "links": {"ontology": "https://data.biodivportal.gfbio.org/ontologies/NCBITAXON"}
        },
        "annotations": [{"text": "AB", "matchType": "EXACT", "from": 1, "to": 2}]
    }]
    result = simplify_response(api_result, "Genus")
    assert result[0]["suspicious_short_match"] is True

def test_simplify_response_not_suspicious_long_match():
    api_result = [{
        "annotatedClass": {
            "@id": "http://x.org/1",
            "links": {"ontology": "https://data.biodivportal.gfbio.org/ontologies/NCBITAXON"}
        },
        "annotations": [{"text": "Hieracium", "matchType": "EXACT", "from": 1, "to": 9}]
    }]
    result = simplify_response(api_result, "Genus")
    assert result[0]["suspicious_short_match"] is False

#  annotate_term (mocked) 

def test_annotate_term_success():
    mock_response = [{"annotatedClass": {"@id": "http://x.org/1", "links": {}}, "annotations": []}]
    with patch("annotate_biodiv.ask_annotator", return_value=mock_response):
        result = annotate_term("Hieracium", api_key="testkey")
    assert result["term"] == "Hieracium"
    assert result["api_result"] == mock_response

def test_annotate_term_api_error():
    import requests
    with patch("annotate_biodiv.ask_annotator", side_effect=requests.RequestException("timeout")):
        result = annotate_term("Hieracium", api_key="testkey")
    assert result["api_result"] == []
    assert "api_error" in result["error"]

def test_annotate_term_unexpected_error():
    with patch("annotate_biodiv.ask_annotator", side_effect=Exception("unexpected")):
        result = annotate_term("Hieracium", api_key="testkey")
    assert result["api_result"] == []
    assert "unexpected_error" in result["error"]

def test_annotate_term_with_ontology_filter():
    mock_response = []
    with patch("annotate_biodiv.ask_annotator", return_value=mock_response) as mock:
        annotate_term("Hieracium", api_key="testkey", ontology="NCBITAXON")
        mock.assert_called_once_with("Hieracium", ontology="NCBITAXON")

#  save_enriched_csv 

def test_save_enriched_csv_creates_uri_columns():
    rows = [{"HerbariumID": "B1", "Genus": "Hieracium", "Family": "ASTERACEAE"}]
    annotated = [{
        "record_id": "B1",
        "annotations": [
            {"source_field": "Genus", "class_id": "http://x.org/1", "matched_text": "Hieracium", "ontology": "NCBITAXON"}
        ]
    }]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        out_path = f.name
    save_enriched_csv(rows, annotated, out_path)
    with open(out_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
    assert "Genus_URI" in headers
    assert "Family_URI" in headers

def test_save_enriched_csv_uri_value_correct():
    rows = [{"HerbariumID": "B1", "Genus": "Hieracium", "Family": "ASTERACEAE"}]
    annotated = [{
        "record_id": "B1",
        "annotations": [
            {"source_field": "Genus", "class_id": "http://x.org/1", "matched_text": "Hieracium", "ontology": "NCBITAXON"}
        ]
    }]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        out_path = f.name
    save_enriched_csv(rows, annotated, out_path)
    with open(out_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        row = next(reader)
    assert row["Genus_URI"] == "http://x.org/1"

def test_save_enriched_csv_empty_uri_when_no_annotation():
    rows = [{"HerbariumID": "B1", "Genus": "Hieracium", "Family": "ASTERACEAE"}]
    annotated = [{"record_id": "B1", "annotations": []}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        out_path = f.name
    save_enriched_csv(rows, annotated, out_path)
    with open(out_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        row = next(reader)
    assert row["Genus_URI"] == ""

def test_save_enriched_csv_empty_rows():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        out_path = f.name
    save_enriched_csv([], [], out_path)
    assert os.path.exists(out_path)

def test_save_enriched_csv_original_columns_preserved():
    rows = [{"HerbariumID": "B1", "Genus": "Hieracium", "Bild": "http://img.org/1"}]
    annotated = [{"record_id": "B1", "annotations": []}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        out_path = f.name
    save_enriched_csv(rows, annotated, out_path)
    with open(out_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        row = next(reader)
    assert row["HerbariumID"] == "B1"
    assert row["Bild"] == "http://img.org/1"