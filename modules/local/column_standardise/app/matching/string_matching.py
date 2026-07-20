"""
String matching and text normalization utilities.

This module provides lexical matching helpers used by the mapping pipeline.
It normalizes input headers, expands common abbreviations and German domain
terms, splits camel-case ABCD terms, and computes fuzzy string similarities
with RapidFuzz.
"""

import re
from rapidfuzz import fuzz


def normalize_text(text):
    """
    Normalize free-form header or surface-form text for matching.

    The function lowercases text, splits camel-case words, replaces selected
    German terms and abbreviations with English equivalents, removes unsupported
    characters, and collapses repeated whitespace.

    Args:
        text: Input text to normalize.

    Returns:
        Normalized text string.
    """
    text = str(text)

    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = text.lower()

    replacements = {
        r"\bsammlerteam\b": "collector team",
        r"\bsammler\b": "collector",
        r"\bsammelnummer\b": "collection number",
        r"\bbild\b": "image",
        r"\bdb\b": "database",
        r"\bfundort\b": "locality",
        r"\boeko\b": "ecology habitat",
        r"\böko\b": "ecology habitat",
        r"\blat\b": "latitude",
        r"\blon\b": "longitude",
        r"\blng\b": "longitude",
        r"\buri\b": "uri link",
        r"\bspec\b": "species",
        r"\banmerkungen\b": "notes remarks comments",
        r"\btiteletikett\b": "label title text",
        r"\bexpeditionsangabe\b": "project expedition survey",
    }

    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)

    text = re.sub(r"[^a-z0-9äöüß ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def split_term(term):
    """
    Normalize an ABCD term name for lexical comparison.

    Args:
        term: ABCD term name, usually written in camel case.

    Returns:
        Lowercase term string with camel-case boundaries split into words.
    """
    term = str(term)
    term = re.sub(r"([a-z])([A-Z])", r"\1 \2", term)
    term = term.lower()
    term = re.sub(r"[^a-z0-9 ]", " ", term)
    term = re.sub(r"\s+", " ", term).strip()
    return term


def string_similarity(a, b):
    """
    Compute fuzzy string similarity between two normalized texts.

    Several RapidFuzz similarity metrics are evaluated, and the highest score is
    returned as a value between 0.0 and 1.0.

    Args:
        a: First input string.
        b: Second input string.

    Returns:
        Maximum fuzzy similarity score normalized to the range 0.0 to 1.0.
    """
    a = normalize_text(a)
    b = normalize_text(b)

    scores = [
        fuzz.ratio(a, b),
        fuzz.partial_ratio(a, b),
        fuzz.token_sort_ratio(a, b),
        fuzz.token_set_ratio(a, b),
    ]

    return max(scores) / 100


def term_string_similarity(header, term):
    """
    Compute fuzzy string similarity between a header and an ABCD term.

    The header is normalized with ``normalize_text``, while the ABCD term is
    normalized with ``split_term`` before comparison.

    Args:
        header: Original input column header.
        term: Candidate ABCD term.

    Returns:
        Maximum fuzzy similarity score normalized to the range 0.0 to 1.0.
    """
    h = normalize_text(header)
    t = split_term(term)

    scores = [
        fuzz.ratio(h, t),
        fuzz.partial_ratio(h, t),
        fuzz.token_sort_ratio(h, t),
        fuzz.token_set_ratio(h, t),
    ]

    return max(scores) / 100
