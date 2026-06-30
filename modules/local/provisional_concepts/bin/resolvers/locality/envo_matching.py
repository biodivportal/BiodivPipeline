# from clients.envo_client import # api functions/class

# still gotta add all the libraries to the requirements.txt

import json
import os
import pickle
import numpy as np
import torch
from pathlib import Path
from sentence_transformers import SentenceTransformer

from clients.envo_client import load_envo_cache, tree_search, semantic_search

# config
REPO_ROOT  = Path(__file__).parent.parent.parent
DATA_DIR   = REPO_ROOT / "data"
ENVO_PATH  = DATA_DIR / "envo_relevant_terms.json"
CACHE_PATH = DATA_DIR / "envo_embeddings.pkl"

TOP_K = 3

MODEL_NAME = "intfloat/multilingual-e5-large"

model           = None
envo_terms      = None
envo_embeddings = None

def get_model():
    global model
    if model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")
        model = SentenceTransformer(MODEL_NAME, device=device)
    return model

# envo text (only label and their synonyms cause descriptions were adding noise)
def build_envo_text(term):
    parts = [term.get("label", "")]
    synonyms = term.get("synonyms", [])
    if synonyms:
        parts.extend(synonyms)
    return " ".join(parts)

def build_envo_embeddings(terms, cache_path=CACHE_PATH):
    # computes embeddings for all envo terms and caches them as files (since performance heavy step)
    envo_texts = [build_envo_text(t) for t in terms]

    print("Computing ENVO embeddings...")
    embeddings = get_model().encode(
        ["passage: " + t for t in envo_texts],
        batch_size=64,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "wb") as f:
        pickle.dump(embeddings, f)

    print(f"Saved embeddings for {len(terms)} ENVO terms to {cache_path}")
    return embeddings

def load_resources():
    # load terms and embeddings or skip if already there
    global envo_terms, envo_embeddings

    if envo_terms is not None and envo_embeddings is not None:
        return

    print("Loading ENVO terms...")
    envo_terms = load_envo_cache(ENVO_PATH)

    if CACHE_PATH.exists():
        print("Loading cached embeddings...")
        with open(CACHE_PATH, "rb") as f:
            envo_embeddings = pickle.load(f)

        if len(envo_embeddings) != len(envo_terms):
            print("Cached embeddings don't match current ENVO terms, rebuilding...")
            envo_embeddings = build_envo_embeddings(envo_terms)
    else:
        envo_embeddings = build_envo_embeddings(envo_terms)

def embedding_search(query, top_k=TOP_K):
    load_resources()

    vec = get_model().encode(
        ["query: " + query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )[0]

    scores = envo_embeddings @ vec
    idx    = np.argsort(scores)[::-1][:top_k]

    return [{"score": float(scores[i]), **envo_terms[i]} for i in idx]

def match_envo(clean_field):
# finding best match in 3 stages
    
    if not clean_field:
            return {"method": None, "matches": []}

    #    # 1. check against local cache (is very very slow)
    #hits = tree_search(clean_field, ENVO_PATH)

    #if hits:
    #    return {"method": "tree_search", "matches": hits}

    # 2. embedding similarity score
    hits = embedding_search(clean_field)
    if hits:
        return {"method": "embedding", "matches": hits}

    ## 3. OLS (could include it later but scoring is missing in step 2 right now)
    #hits = semantic_search(clean_field)
    #if hits:
    #    return {"method": "ols_api", "matches": hits}
    #return {"method": None, "matches": []}

# if __name__ == "__main__":
#     test_queries = [
#         "Sportplatz im Ödland",
#         "Sportplatz",
#         "Ödland",
#         "Oedland"
#     ]
#     for q in test_queries:
#         result = match_envo(q)
#         print(f"\n{q} → [{result['method']}]")
#         for m in result["matches"]:
#             print(f"  {m.get('score', '-'):.4f} | {m.get('label')} | {m.get('obo_id')}")