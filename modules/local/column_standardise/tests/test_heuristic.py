from app.matching.heuristic_matching import heuristic_bonus


def test_heuristic_bonus():
    # Matching id structural heuristic (using actual rules from heuristic_rules.json)
    assert heuristic_bonus("Latitude", "LatitudeDecimal") > 0.0
    # No heuristic match
    assert heuristic_bonus("Latitude", "LongitudeDecimal") == 0.0
