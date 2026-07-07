from .cleaner import split_locality_label
from .place_filter import filter_placenames
from .envo_matching import match_envo


def _score_row(row, config=None, llm_split=None):
    source_field = row.get("source_field", "")
    original_term = row.get("original_term", "")

    if llm_split is None:
        llm_split = split_locality_label([original_term])[0]

    location_text = llm_split.get("location", "").strip()
    clean_locality = llm_split.get("environment", "").strip()

    _, geonames_matches = filter_placenames(location_text)
    geonames_data = list(geonames_matches.values())

    envo_result = match_envo(clean_locality)
    matches = envo_result.get("matches", [])

    best_similarity = 0.0
    matched_label = None
    matched_iri = None
    matched_obo_id = None

    if matches:
        best_match = matches[0]
        best_similarity = best_match.get("score", 0.0)
        matched_label = best_match.get("label")
        matched_iri = best_match.get("iri")
        matched_obo_id = best_match.get("obo_id")
    weight = 0.5
    """
    # The score from the annotator doesn't match geonames or envo
    if config and source_field in config:
        weight = config[source_field].get("score", 0.5)
    """

    explanation_parts = []
    if geonames_data:
        loc_names = ", ".join(
            [loc.get("name", "") for loc in geonames_data if loc.get("name")]
        )
        explanation_parts.append(f"Location near: {loc_names} [from geonames].")

    if best_similarity >= 0.82:
        proposed_action = "DISCARD"
        ontology_inclusion_score = 0.0
        proposed_concept_name = matched_label
        explanation_parts.append(
            f"'{clean_locality}' matched semantically to ENVO term '{matched_label}' ({matched_obo_id}) with {best_similarity*100:.1f}% confidence."
        )
    else:
        proposed_action = "REGISTER"
        ontology_inclusion_score = weight * (1.0 - best_similarity)
        # Here the definition is to be added using an LLM
        proposed_concept_name = clean_locality or original_term
        if matched_label:
            explanation_parts.append(
                f"No matching ENVO term found above threshold (highest match was '{matched_label}' with {best_similarity*100:.1f}% confidence). Suggested to register new concept."
            )
        else:
            explanation_parts.append(
                "No matching ENVO term found. Suggested to register new concept."
            )

    envo_resolution = {
        "matched_term_label": matched_label,
        "matched_term_id": matched_obo_id,
        "matched_term_uri": matched_iri,
        "similarity_score": best_similarity,
        "ols_match_type": envo_result.get("method"),
    }

    locality_metadata = {
        "geonamedata": geonames_data,
        "text_cleaning": {"cleaned_environmental_descriptor": clean_locality},
        "llm_split": llm_split,
        "envo_resolution": envo_resolution,
    }

    return {
        **row,
        "source_field": source_field,
        "original_term": original_term,
        "locationURI": None,
        "locationName": None,
        "proposed_concept_name": proposed_concept_name,
        "proposed_concept_rank": "ENVIRONMENT",
        "proposed_action": proposed_action,
        "ontology_inclusion_score": ontology_inclusion_score,
        "explanation": " ".join(explanation_parts),
        "locality_metadata": locality_metadata,
    }


def score(rows, config=None):
    if not rows:
        return []
    original_terms = [r.get("original_term", "") for r in rows]
    llm_splits = split_locality_label(original_terms)
    return [
        _score_row(r, config, llm_split=split) for r, split in zip(rows, llm_splits)
    ]
