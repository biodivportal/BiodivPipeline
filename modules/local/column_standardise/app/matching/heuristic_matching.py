"""
Rule-based heuristic matching utilities.

This module applies manually defined heuristic rules to strengthen mapping
predictions when characteristic keywords or naming patterns are detected in
input headers. The rules are loaded from ``heuristic_rules.json`` and provide
additional score bonuses for matching ABCD terms.
"""

import json
from pathlib import Path
from app.matching.string_matching import normalize_text, split_term

CONFIG_DIR = Path(__file__).parent.parent / "config"
HEURISTIC_RULES_FILE = CONFIG_DIR / "heuristic_rules.json"

with open(HEURISTIC_RULES_FILE, "r") as f:
    HEURISTIC_RULES = json.load(f)


def heuristic_bonus(header, term):
    """
    Calculate the heuristic score bonus for a candidate ABCD term.

    The function compares the normalized input header against a set of
    predefined heuristic rules. If a rule matches both the header and the
    candidate term, the corresponding bonus is added to the final score.

    Args:
        header: Original input column header.
        term: Candidate ABCD term.

    Returns:
        Total heuristic bonus for the given header-term combination.
    """
    h = normalize_text(header)
    t = split_term(term)

    bonus = 0.0

    for rule in HEURISTIC_RULES:
        if rule["header_keyword"] in h:
            if "term_keyword" in rule and rule["term_keyword"] in t:
                bonus += rule["bonus"]
            elif "exact_terms" in rule and term in rule["exact_terms"]:
                bonus += rule["bonus"]

    return bonus
