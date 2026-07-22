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

REPO_ROOT = Path(__file__).parent.parent
DATA_DIR   = REPO_ROOT / "data"
CACHE_PATH = DATA_DIR / "envo_relevant_terms.json"

HABITAT_ROOT_IRIS = {
    "http://purl.obolibrary.org/obo/ENVO_01000254",  # environmental system
    "http://purl.obolibrary.org/obo/ENVO_00000446",  # biome
    "http://purl.obolibrary.org/obo/ENVO_00000873",  # aquatic biome
    "http://purl.obolibrary.org/obo/ENVO_00002010",  # terrestrial biome
    "http://purl.obolibrary.org/obo/ENVO_00000063",  # water body
    "http://purl.obolibrary.org/obo/ENVO_01000617",  # lentic water body
    "http://purl.obolibrary.org/obo/ENVO_01001243",  # forest ecosystem
    "http://purl.obolibrary.org/obo/ENVO_01000177",  # grassland ecosystem
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


def simplify_term(term: Dict[str, Any], is_habitat: bool = False) -> Dict[str, Any]:
# keeps only the fields needed by WP5 matching/scoring
    return {
        "label": term.get("label"),
        "iri": term.get("iri"),
        "obo_id": term.get("obo_id"),
        "description": term.get("description", []),
        "synonyms": term.get("synonyms", []) or term.get("synonym", []),
        "is_habitat": is_habitat,
    }


def _fetch_all_terms() -> List[Dict[str, Any]]:
    terms: Dict[str, Dict[str, Any]] = {}
    page = 0
    while True:
        response = requests.get(
            f"{OLS_BASE_URL}/ontologies/{ONTOLOGY}/terms",
            params={"page": page, "size": 500},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        chunk = data.get("_embedded", {}).get("terms", [])
        for term in chunk:
            iri = term.get("iri")
            if not iri or not term.get("label") or "/ENVO_" not in iri or term.get("is_obsolete"):
                continue
            terms.setdefault(iri, term)
        total_pages = data.get("page", {}).get("totalPages", 1)
        page += 1
        if page >= total_pages or len(chunk) < 500:
            break
    return list(terms.values())


def _fetch_habitat_iris() -> set:
    iris = set()
    for root_iri in HABITAT_ROOT_IRIS:
        for term in get_descendants(root_iri):
            iri = term.get("iri")
            if iri and "/ENVO_" in iri:
                iris.add(iri)
    return iris


def build_envo_cache(cache_path: Path = CACHE_PATH) -> List[Dict[str, Any]]:
# Whole-ENVO cache (all non-obsolete terms) with an is_habitat tag (descendant of a habitat root).
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    habitat_iris = _fetch_habitat_iris()
    raw = _fetch_all_terms()
    cached_terms = [simplify_term(t, is_habitat=(t.get("iri") in habitat_iris)) for t in raw]

    with open(cache_path, "w", encoding="utf-8") as file:
        json.dump(cached_terms, file, indent=2, ensure_ascii=False)

    n_habitat = sum(1 for t in cached_terms if t["is_habitat"])
    print(f"Saved {len(cached_terms)} ENVO terms ({n_habitat} habitat) to {cache_path}")
    return cached_terms


def load_envo_cache(cache_path: Path = CACHE_PATH) -> List[Dict[str, Any]]:
# Load the local relevant ENVO cache and build if missing
    if not cache_path.exists():
        return build_envo_cache(cache_path)

    with open(cache_path, "r", encoding="utf-8") as file:
        return json.load(file)

def tree_search(term, cache_path=CACHE_PATH):
# search against labels and synonyms i local cache
    query = term.lower().strip()
    matches = []

    for entry in load_envo_cache(cache_path):
        label = (entry.get("label") or "").lower()
        synonyms = [s.lower() for s in entry.get("synonyms", []) if isinstance(s, str)]

        if query == label or query in label or query in synonyms:
            matches.append(entry)

    return matches

#def tree_search(term: str) -> List[Dict[str, Any]]:
# Search inside the locally cached relevant ENVO tree
#    return search_cached_envo(term)

# if __name__ == "__main__":
#     term = "tidal creek"
#     matches = tree_search(term)
#     print(f"tree_search('{term}'): {len(matches)} match(es)")
#     for m in matches:
#         print(f"  {m['label']} — {m['iri']}")