from clients.gbif_client import species_match
import re

# Find author annotation pointing to non classified entries
DOUBT_REGEX = re.compile(
    r"\b(cf|aff|indet|spp?|spec|hort|s\.\s*s|s\.\s*l|s\.\s*str)\b\.?", re.IGNORECASE
)
# Find infraspecific epithets
INFRASPECIFIC_REGEX = re.compile(
    r"(?<!\S)(var\.|subsp\.|ssp\.|f\.|nothovar\.|nothosubsp\.|subvar\.|subf\.|sbf\.|v\.)\s+([a-zA-Z-]+)", re.IGNORECASE
)

# GBIF Backbone normalises following this map (name_lookup doesn't!)
INFRASPECIFIC_RANK_MAP = {
    "subsp.": "subspecies",
    "ssp.": "subspecies",
    "nothosubsp.": "subspecies",
    "var.": "variety",
    "v.": "variety",
    "nothovar.": "variety",
    "subvar.": "subvariety",
    "f.": "forma",
    # TODO: Manage subforma
    # "subf.": "subforma",
    # "sbf.": "subforma"
}

EMPTY_TAXONOMY = {
    "family": None,
    "genus": None,
    "species": None,
    "subspecies": None,
    "variety": None,
    "subvariety": None,
    "forma": None,
    "subforma": None,
}


def extract_infraspecific_epithets(term):
    """Extracts infraspecific epithets from the source name. See DwC"""
    extracted = {}

    if not term:
        return extracted

    for match in INFRASPECIFIC_REGEX.finditer(term):
        indicator = match.group(1).lower()
        key = INFRASPECIFIC_RANK_MAP.get(indicator)
        if key:
            extracted[key] = match.group(2)

    return extracted


def extract_gbif_taxonomy(gbif_classification):
    taxa = EMPTY_TAXONOMY.copy()

    if not gbif_classification:
        return taxa

    for item in gbif_classification:
        rank = item.get("rank", "").lower()
        name = item.get("name")

        if rank == "form":
            rank = "forma"  # Fix for GBIF using FORM
        if rank in taxa.keys():
            taxa[rank] = name
        elif rank not in ["kingdom", "phylum", "class", "order"]:
            print(f"An un recognised rank was returned by GBIF : {rank}")

    return taxa


def extract_source_taxonomy(row):
    """Extract the taxonomic classification of the row"""
    taxonomy = EMPTY_TAXONOMY.copy()

    taxonomy["family"] = row.get("family", None)
    taxonomy["genus"] = row.get("genus", None)

    term_to_parse = row.get("name") or row.get("fullname")

    # TODO: Fails on hybrids
    if term_to_parse:
        clean_words = term_to_parse.split()

        if len(clean_words) > 0 and not taxonomy["genus"]:
            # Don't overwritte if input contains genus
            taxonomy["genus"] = clean_words[0]
        if len(clean_words) > 1:
            taxonomy["species"] = f"{clean_words[0]} {clean_words[1]}"

        infraspecifics = extract_infraspecific_epithets(term_to_parse)
        taxonomy.update(infraspecifics)

    return taxonomy


def get_target_rank(source_field, source_taxonomy):
    """Depending on the parsed source name choose lowest rank as target"""
    if source_field in ["Family", "Genus"]:
        return source_field

    if source_field in ["FullNameCache", "NameCache"]:
        for rank in ["forma", "subvariety", "variety", "subspecies"]:
            if source_taxonomy.get(rank):
                return rank
        return "species"

    return "unknown"


def score(row, ontology_config):
    """
    Scores and provides recommendation on whether to register an unresolved term as a provisional concept.
    """
    source_field = row.get("unresolved_terms") or "FullNameCache"
    # currently run once for a specific species
    if isinstance(source_field, list):
        for f in ["FullNameCache", "NameCache", "Genus", "Family"]:
            if f in source_field:
                source_field = f
                break
        else:
            source_field = "FullNameCache"
    source_term = row["row"].get(source_field) or row.get("fullname") or ""

    source_taxonomy = extract_source_taxonomy(row)
    target_rank = get_target_rank(source_field, source_taxonomy)

    if target_rank == "unknown":
        tax = EMPTY_TAXONOMY.copy()
        return {
            **row,
            "source_field": source_field,
            "original_term": source_term,
            "source_taxonomy": source_taxonomy,
            "proposed_concept_name": None,
            "proposed_concept_rank": "unknown",
            "gbif_taxonomy": tax,
            "gbif_match_score": 0.0,
            "ontology_inclusion_score": 0.0,
            "proposed_action": "DISCARD",
            "explanation": f"Source field '{source_field}' is not a taxonomic target.",
        }

    fullname = (
        row.get("fullname") or source_term
    )
    gbif_match = species_match(source_taxonomy, fullname, target_rank)

    diagnostics = gbif_match.get("diagnostics", {})
    match_type = diagnostics.get("matchType", "NONE")

    synonym = gbif_match.get("synonym", False)
    usage = gbif_match.get("usage", {})
    gbif_rank = usage.get("rank", "unknown").lower()
    if gbif_rank == "form":
        gbif_rank = "forma"

    gbif_classification = gbif_match.get("classification", None)
    gbif_taxonomy = extract_gbif_taxonomy(gbif_classification)

    # get the accepted term according to GBIF "acceptedUsage" includes authorship
    if synonym:
        usage_name = gbif_match.get("acceptedUsage", {}).get("name", None)
    else:
        usage_name = gbif_taxonomy.get(target_rank)

    is_rank_mismatch = gbif_rank != target_rank

    source_target_name = source_taxonomy.get(target_rank.lower())
    proposed_target_name = gbif_taxonomy.get(target_rank.lower())
    is_reclassified = (
        source_target_name
        and proposed_target_name
        and source_target_name.lower() != proposed_target_name.lower()
    )

    if is_rank_mismatch or match_type == "NONE":
        proposed_concept_name = source_term
        proposed_concept_rank = target_rank
    else:
        proposed_concept_name = usage_name
        proposed_concept_rank = gbif_rank

    explanation_parts = []

    if not proposed_concept_name:
        match_type = "NONE"

    # Scoring
    match_scores = {"NONE": 0.0, "EXACT": 1.0, "FUZZY": 0.8, "HIGHERRANK": 0.5}
    gbif_confidence = diagnostics.get("confidence", 0) / 100.0
    gbif_match_score = match_scores.get(match_type, gbif_confidence)

    explanations = {
        "NONE": f"No match found for target rank ({target_rank}).",
        "EXACT": "Exact match in GBIF.",
        "FUZZY": "Fuzzy match in GBIF.",
        "HIGHERRANK": f"Matched at a higher rank ({gbif_rank}).",
    }
    explanation_parts.append(
        explanations.get(match_type, f"GBIF match type: {match_type}.")
    )

    ontology_match_score = ontology_config.get(source_field, {}).get("score")

    base_score, proposed_action = 1.0, "REGISTER"

    if synonym:
        base_score, proposed_action, proposed_concept_name = 0.0, "DISCARD", source_term
        explanation_parts.append(
            f'"{source_term}" is a synonym for accepted term "{usage_name}".'
        )
    elif is_reclassified:
        base_score, proposed_action, proposed_concept_name = 0.0, "DISCARD", source_term
        explanation_parts.append(
            f'"{source_target_name}" was resolved as "{proposed_target_name}" (reclassified or spelling variant).'
        )
    elif match_type == "NONE":
        base_score, proposed_concept_name = 0.5, source_term
    elif is_rank_mismatch:
        base_score = 0.8
        explanation_parts.append("Suggests specific concept is missing.")
    else:
        explanation_parts.append("Confirmed as accepted term.")

    ontology_inclusion_score = (
        base_score * gbif_confidence * ontology_match_score * gbif_match_score
    )

    has_doubt = bool(
        DOUBT_REGEX.search(source_term)
    )  # Might not have been classified by author

    if has_doubt and proposed_action == "REGISTER":
        ontology_inclusion_score *= 0.8
        proposed_action = "REVIEW"
        explanation_parts.append("Author hasn't fully classified the specimen.")

    return {
        **row,
        "source_field": source_field,
        "original_term": source_term,
        "source_taxonomy": source_taxonomy,
        "proposed_concept_name": proposed_concept_name,
        "proposed_concept_rank": proposed_concept_rank,
        "gbif_taxonomy": gbif_taxonomy,
        "gbif_confidence": gbif_confidence,
        "ontology_match_score": ontology_match_score,
        "ontology_inclusion_score": ontology_inclusion_score,
        "proposed_action": proposed_action,
        "explanation": " ".join(explanation_parts),
    }
