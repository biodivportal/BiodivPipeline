from .cleaner import split_locality_label
from .place_filter import filter_placenames
from .envo_matching import match_envo, FINAL_TOP_K
from .judge import judge_concepts

CONFIDENCE_SCORE = {"high": 0.9, "medium": 0.6, "low": 0.3}


def _source_field(row):
    sf = row.get("unresolved_terms") or "Locality"
    if isinstance(sf, list):
        for f in ("Locality", "FundortUNdOeko"):
            if f in sf:
                return f
        return "Locality"
    return sf


def _read_clc(row):
    r = row.get("row") or {}
    return {
        "code": (r.get("llm_code") or "").strip(),
        "name": (r.get("llm_name") or "").strip(),
        "conf": (r.get("llm_confidence") or "").strip(),
    }


def _clc_str(clc):
    if not clc.get("name"):
        return ""
    label = f"{clc['code']} = {clc['name']}" if clc.get("code") else clc["name"]
    return f"Upstream CLC: {label}" + (f" ({clc['conf']})" if clc.get("conf") else "") + "."


def _geonames(split, row):
    location_text = split.get("location", "").strip()
    r = row.get("row") or {}
    country = r.get("Country") or r.get("example_Country")
    _, matches = filter_placenames(location_text, country_name=country)
    return list(matches.values())


def _envo_resolution(candidates, match_idx):
    matched = None
    if match_idx is not None and 0 <= match_idx < len(candidates):
        matched = candidates[match_idx]
    if matched is None:
        score = candidates[0].get("rerank_score", 0.0) if candidates else 0.0
        matched_label = matched_iri = matched_obo = None
    else:
        matched_label = matched.get("label")
        matched_iri = matched.get("iri")
        matched_obo = matched.get("obo_id")
        score = matched.get("rerank_score", 0.0)
    return {
        "matched_term_label": matched_label,
        "matched_term_id": matched_obo,
        "matched_term_uri": matched_iri,
        "similarity_score": score,
        "ols_match_type": "embedding+rerank",
        "top_candidates": [
            {"label": c.get("label"), "obo_id": c.get("obo_id"),
             "score": c.get("rerank_score", c.get("score", 0.0)), "is_habitat": c.get("is_habitat")}
            for c in candidates
        ],
    }


def _base(row, split, geonames_data, clc):
    return {
        **row,
        "source_field": _source_field(row),
        "original_term": ", ".join(loc for loc in row.get("locality", []) if loc),
        "proposed_concept_rank": "ENVIRONMENT",
        "translated_term": "",
        "definition": "",
        "proposed_synonyms": [],
        "clc_code": clc.get("code", ""),
        "clc_name": clc.get("name", ""),
        "locality_metadata": {"geonamedata": geonames_data, "llm_split": split, "envo_resolution": {}},
    }


def _discard_row(row, split, geonames_data, clc):
    rec = _base(row, split, geonames_data, clc)
    rec["locality_metadata"]["envo_resolution"] = _envo_resolution([], None)
    rec.update({
        "proposed_concept_name": "",
        "proposed_action": "DISCARD",
        "ontology_inclusion_score": 0.0,
        "explanation": "No environment/habitat description found in the locality text; place-name only.",
    })
    return rec


def _judged_row(row, split, geonames_data, clc, candidates, env_de, env_en, verdict):
    verdict = verdict if isinstance(verdict, dict) else {}
    raw_match = verdict.get("match")
    match_idx = raw_match - 1 if isinstance(raw_match, int) else None
    disposition = (verdict.get("disposition") or "").lower()
    conf = verdict.get("confidence", "low")
    justification = (verdict.get("justification") or "").strip()

    parts = []
    if justification:
        parts.append(justification)
    clc_s = _clc_str(clc)
    if clc_s:
        parts.append(clc_s)
    explanation = " ".join(parts)

    envo_resolution = _envo_resolution(candidates, match_idx)
    rec = _base(row, split, geonames_data, clc)
    rec["locality_metadata"]["envo_resolution"] = envo_resolution
    rec["translated_term"] = env_en

    if disposition == "accept" and match_idx is not None:
        rec.update({
            "proposed_concept_name": envo_resolution["matched_term_label"],
            "proposed_action": "ACCEPT",
            "ontology_inclusion_score": CONFIDENCE_SCORE.get(conf, 0.3),
            "explanation": explanation,
            "proposed_synonyms": [env_de] if env_de else [],
        })
    elif disposition == "register":
        rec.update({
            "proposed_concept_name": env_en or env_de,
            "proposed_action": "REGISTER",
            "ontology_inclusion_score": CONFIDENCE_SCORE.get(conf, 0.3),
            "explanation": explanation,
            "definition": (verdict.get("definition") or "").strip(),
            "proposed_synonyms": [env_de] if env_de else [],
        })
    else:
        rec.update({
            "proposed_concept_name": "",
            "proposed_action": "DISCARD",
            "ontology_inclusion_score": 0.0,
            "explanation": explanation or "Judge: not an environment/habitat concept.",
            "proposed_synonyms": [],
        })
    return rec


def score(rows, config=None):
    if not rows:
        return []
    original_terms = [", ".join(loc for loc in r.get("locality", []) if loc) for r in rows]
    splits = split_locality_label(original_terms)

    results = [None] * len(rows)
    pending = []
    for i, (row, split) in enumerate(zip(rows, splits)):
        env_de = (split.get("environment") or "").strip()
        clc = _read_clc(row)
        geonames_data = _geonames(split, row)
        if not env_de:
            results[i] = _discard_row(row, split, geonames_data, clc)
            continue
        env_en = (split.get("environment_EN") or "").strip()
        envo = match_envo(env_de, query_en=env_en or None)
        candidates = envo.get("matches", [])[:FINAL_TOP_K]
        pending.append((i, row, split, geonames_data, clc, candidates, env_de, env_en))

    verdicts = judge_concepts([
        {"german": env_de, "english": env_en, "candidates": cands, "clc": clc}
        for (_, _, _, _, clc, cands, env_de, env_en) in pending
    ])

    for (i, row, split, geonames_data, clc, candidates, env_de, env_en), verdict in zip(pending, verdicts):
        results[i] = _judged_row(row, split, geonames_data, clc, candidates, env_de, env_en, verdict)

    return [r for r in results if r is not None]
