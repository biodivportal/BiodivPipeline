"""
export_csv.py - Export provisional_concepts.json to a clean readable CSV
Combines taxon and locality results into a single unified CSV format.
"""

import csv
import json
import argparse
from pathlib import Path


def extract_row(concept):
    is_locality = "locality_metadata" in concept or concept.get("proposed_concept_rank") == "ENVIRONMENT"

    row_type = "locality" if is_locality else "taxon"
    source_field = concept.get("source_field", "")
    original_term = concept.get("original_term", "")
    proposed_concept_name = concept.get("proposed_concept_name", "")
    proposed_concept_rank = concept.get("proposed_concept_rank", "")
    proposed_action = concept.get("proposed_action", "")
    ontology_inclusion_score = round(concept.get("ontology_inclusion_score", 0.0), 3)
    explanation = concept.get("explanation", "")

    if is_locality:
        # envo
        envo = concept.get("locality_metadata", {}).get("envo_resolution", {})
        match_term = envo.get("matched_term_label", "") or ""
        match_uri = envo.get("matched_term_uri", "") or ""
        match_confidence = round(envo.get("similarity_score", 0.0), 3)
        match_method = envo.get("ols_match_type", "") or ""

        # geonames
        geo_data = concept.get("locality_metadata", {}).get("geonamedata", [])
        resolved_locations = ", ".join([g.get("name", "") for g in geo_data if g.get("name")])
        location_uris = ", ".join([g.get("uri", "") for g in geo_data if g.get("uri")])

        # details column
        llm_split = concept.get("locality_metadata", {}).get("llm_split", {})
        split_location = llm_split.get("location", "").replace(";", ",").strip()
        split_environment = llm_split.get("environment", "").replace(";", ",").strip()
        geonames_count = len(geo_data)
        details = f"split_location={split_location}; split_environment={split_environment}; geonames_count={geonames_count}"
    else:
        # taxon fields
        match_term = concept.get("proposed_concept_name", "")
        usage_key = concept.get("gbif_usage_key")
        match_uri = f"https://www.gbif.org/species/{usage_key}" if usage_key else ""
        match_confidence = round(concept.get("gbif_confidence", 0.0), 3)
        match_method = concept.get("gbif_match_type", "")

        resolved_locations = ""
        location_uris = ""

        # details column
        gbif_tax = concept.get("gbif_taxonomy", {})
        family = gbif_tax.get("family", "") or ""
        genus = gbif_tax.get("genus", "") or ""
        details = f"family={family}; genus={genus}; gbif_match_type={match_method}"

    return {
        "type": row_type,
        "source_field": source_field,
        "original_term": original_term,
        "proposed_concept_name": proposed_concept_name,
        "proposed_concept_rank": proposed_concept_rank,
        "proposed_action": proposed_action,
        "ontology_inclusion_score": ontology_inclusion_score,
        "explanation": explanation,
        "match_term": match_term,
        "match_uri": match_uri,
        "match_confidence": match_confidence,
        "match_method": match_method,
        "resolved_locations": resolved_locations,
        "location_uris": location_uris,
        "details": details,
    }


def export_concepts_csv(concepts, output_path):
    rows = [extract_row(c) for c in concepts]

    fieldnames = [
        "type",
        "source_field",
        "original_term",
        "proposed_concept_name",
        "proposed_concept_rank",
        "proposed_action",
        "ontology_inclusion_score",
        "explanation",
        "match_term",
        "match_uri",
        "match_confidence",
        "match_method",
        "resolved_locations",
        "location_uris",
        "details",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Export provisional concepts to CSV")
    parser.add_argument("--input", required=True, help="Path to provisional_concepts.json")
    parser.add_argument("--output", required=True, help="Path to output CSV")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)

    concepts = data.get("provisional_concepts", [])
    print(f"[info] Loaded {len(concepts)} concepts")

    export_concepts_csv(concepts, args.output)
    print(f"[done] Saved {len(concepts)} rows to {args.output}")


if __name__ == "__main__":
    main()
