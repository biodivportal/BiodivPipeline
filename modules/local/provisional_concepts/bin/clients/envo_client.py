"""
This script should connect to OLS, it should expose a function that takes a string and return the results of the search.
It should also expose a function that can check whether a term found by the semantic search is within the part of ENVO we're interested in.
Ideally minimal data processing, the resolver should handle it. (though the checks for whether the results are in the part of the ENVO structure that we are interested in should be handled here)
"""
# This is a version of the ENVO client, which loads and caches all relevant ENVO terms (descendants of relevant root classes) locally

import json
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote

import requests


OLS_BASE_URL = "https://www.ebi.ac.uk/ols4/api"
ONTOLOGY = "envo"
REQUEST_TIMEOUT = 30

CLIENT_DIR = Path(__file__).parent
CACHE_PATH = CLIENT_DIR / "envo_relevant_terms.json"

RELEVANT_ROOT_IRIS = {
    # broad environmental concepts
    "http://purl.obolibrary.org/obo/ENVO_01000254", # environmental system
    "http://purl.obolibrary.org/obo/ENVO_00010483", # environmental material

    # aquatic features
    "http://purl.obolibrary.org/obo/ENVO_00000063", # water body
    "http://purl.obolibrary.org/obo/ENVO_01000617", # lentic water body
    "http://purl.obolibrary.org/obo/ENVO_00000022", # river
    "http://purl.obolibrary.org/obo/ENVO_00000023", # stream
    
    # terrestrial environments
    "http://purl.obolibrary.org/obo/ENVO_01001886", # landform
    "http://purl.obolibrary.org/obo/ENVO_00000191", # solid astronomical body part

    # vegetation / habitats
    "http://purl.obolibrary.org/obo/ENVO_01001243",# forest ecosystem
    "http://purl.obolibrary.org/obo/ENVO_01000177",# grassland ecosystem

    # materials
    "http://purl.obolibrary.org/obo/ENVO_00001998",# soil
    "http://purl.obolibrary.org/obo/ENVO_00002007",# sediment
    
    # human influenced environments
    "http://purl.obolibrary.org/obo/ENVO_01000951",# cultivated environment
    
}

def encode_iri(iri: str) -> str:
    return quote(quote(iri, safe=""), safe="")


def get_descendants(root_iri: str) -> List[Dict[str, Any]]:
# Load all descendants/subclasses of one ENVO root class from OLS

    encoded_iri = encode_iri(root_iri)
    url = f"{OLS_BASE_URL}/ontologies/{ONTOLOGY}/terms/{encoded_iri}/descendants"

    descendants: List[Dict[str, Any]] = []
    page = 0

    while True:
        response = requests.get(
            url,
            params={"page": page, "size": 500},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        data = response.json()
        terms = data.get("_embedded", {}).get("terms", [])
        descendants.extend(terms)

        page_info = data.get("page", {})
        total_pages = page_info.get("totalPages", 1)

        page += 1
        if page >= total_pages:
            break

    return descendants


def semantic_search(text: str, rows: int = 10) -> List[Dict[str, Any]]:
# Search ENVO and return raw OLS search results

    response = requests.get(
        f"{OLS_BASE_URL}/search",
        params={
            "q": text,
            "ontology": ONTOLOGY,
            "type": "class",
            "rows": rows,
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    return response.json().get("response", {}).get("docs", [])


def simplify_term(term: Dict[str, Any], root_iri: str) -> Dict[str, Any]:
# keeps only the fields needed by WP5 matching/scoring
    return {
        "label": term.get("label"),
        "iri": term.get("iri"),
        "obo_id": term.get("obo_id"),
        "description": term.get("description", []),
        "synonyms": term.get("synonyms", []) or term.get("synonym", []),
        "root_iri": root_iri,
    }


def build_envo_cache(cache_path: Path = CACHE_PATH) -> List[Dict[str, Any]]:
# Builds a local cache containing all relevant ENVO terms
    all_terms: Dict[str, Dict[str, Any]] = {}

    for root_iri in RELEVANT_ROOT_IRIS:
        print(f"Loading descendants for: {root_iri}")

        for term in get_descendants(root_iri):
            iri = term.get("iri")
            if not iri:
                continue

            all_terms[iri] = simplify_term(term, root_iri)

    cached_terms = list(all_terms.values())

    with open(cache_path, "w", encoding="utf-8") as file:
        json.dump(cached_terms, file, indent=2, ensure_ascii=False)

    print(f"Saved {len(cached_terms)} ENVO terms to {cache_path}")

    return cached_terms


def load_envo_cache(cache_path: Path = CACHE_PATH) -> List[Dict[str, Any]]:
# Load the local relevant ENVO cache.
    if not cache_path.exists():
        return build_envo_cache(cache_path)

    with open(cache_path, "r", encoding="utf-8") as file:
        return json.load(file)


def search_cached_envo(
    term: str,
    cache_path: Path = CACHE_PATH,
) -> List[Dict[str, Any]]:

# Search only inside the locally cached relevant ENVO terms
    query = term.lower().strip()
    cache = load_envo_cache(cache_path)

    matches: List[Dict[str, Any]] = []

    for entry in cache:
        label = (entry.get("label") or "").lower()
        synonyms = [
            synonym.lower()
            for synonym in entry.get("synonyms", [])
            if isinstance(synonym, str)
        ]

        if query == label or query in label or query in synonyms:
            matches.append(entry)

    return matches


def tree_search(term: str) -> List[Dict[str, Any]]:
# Search inside the locally cached relevant ENVO tree
    return search_cached_envo(term)


if __name__ == "__main__":
    # Build/update cache once.
    # build_envo_cache()

    # Simple smoke test.
    term = "tidal creek"
    matches = tree_search(term)

    print(f"\nFound {len(matches)} cached ENVO matches")
    print(f"Search term: {term}\n")

    for index, match in enumerate(matches, start=1):
        print(f"[{index}/{len(matches)}] {match.get('label')}")
        print(match.get("iri"))
        print()