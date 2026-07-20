from app.matching.string_matching import (
    normalize_text,
    split_term,
    string_similarity,
    term_string_similarity,
)


def test_normalize_text():
    # Direct normalization cases
    assert normalize_text("Sammlerteam") == "collector team"
    assert normalize_text("Bild") == "image"
    assert normalize_text("DB") == "database"
    assert normalize_text("Latitude") == "latitude"
    assert normalize_text("Anmerkungen") == "notes remarks comments"


def test_split_term():
    # Test camelCase splitting and stripping
    assert split_term("HerbariumID") == "herbarium id"
    assert split_term("DecimalLatitude") == "decimal latitude"
    assert split_term("decimal latitude") == "decimal latitude"
    assert split_term("Some_Underscore-Text") == "some underscore text"


def test_string_similarity():
    # Test fuzzy matching
    # Exact match
    assert string_similarity("latitude", "latitude") == 1.0
    # High similarity
    assert string_similarity("latitud", "latitude") > 0.8
    # Low similarity
    assert string_similarity("apple", "latitude") < 0.4


def test_term_string_similarity():
    # term_string_similarity uses rapidfuzz internally
    assert term_string_similarity("LatitudeDecimal", "latitude decimal") == 1.0
    assert term_string_similarity("LatitudeDecimal", "latitude decim") > 0.8
    assert term_string_similarity("LatitudeDecimal", "longitude decimal") < 0.95
