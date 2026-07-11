#!/usr/bin/env python3
"""
export_csv.py - Export provisional_concepts.json to a clean readable CSV
Combines GeoNames, ENVO and decision data into one human-readable file
"""

import csv
import json
import argparse
from pathlib import Path


def extract_row(concept):
    # get geonames resolved places
    geo_data = concept.get("locality_metadata", {}).get("geonamedata", [])
    resolved_locations = ", ".join([g.get("name", "") for g in geo_data if g.get("name")])
    location_uris = ", ".join([g.get("uri", "") for g in geo_data if g.get("uri")])
    geonames_count = len(geo_data)

    # get llm split
    llm_split = concept.get("locality_metadata", {}).get("llm_split", {})
    split_location = llm_split.get("location", "")
    split_environment = llm_split.get("environment", "")

    # get envo resolution
    envo = concept.get("locality_metadata", {}).get("envo_resolution", {})
    envo_term = envo.get("matched_term_label", "") or ""
    envo_uri = envo.get("matched_term_uri", "") or ""
    envo_confidence = round(envo.get("similarity_score", 0.0), 3)
    envo_method = envo.get("ols_match_type", "") or ""

    return {
        "source_field": concept.get("source_field", ""),
        "original_term": concept.get("original_term", ""),
        "split_location": split_location,
        "split_environment": split_environment,
        "resolved_locations": resolved_locations,
        "location_uris": location_uris,
        "geonames_count": geonames_count,
        "envo_term": envo_term,
        "envo_uri": envo_uri,
        "envo_confidence": envo_confidence,
        "envo_match_method": envo_method,
        "proposed_concept_name": concept.get("proposed_concept_name", ""),
        "proposed_action": concept.get("proposed_action", ""),
        "explanation": concept.get("explanation", ""),
    }


def main():
    parser = argparse.ArgumentParser(description="Export provisional concepts to CSV")
    parser.add_argument("--input", required=True, help="Path to provisional_concepts.json")
    parser.add_argument("--output", required=True, help="Path to output CSV")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)

    concepts = data.get("provisional_concepts", [])
    print(f"[info] Loaded {len(concepts)} concepts")

    # filter only locality records
    locality_concepts = [c for c in concepts if c.get("locality_metadata")]
    print(f"[info] {len(locality_concepts)} locality records")

    rows = [extract_row(c) for c in locality_concepts]

    fieldnames = [
        "source_field", "original_term", "split_location", "split_environment",
        "resolved_locations", "location_uris", "geonames_count",
        "envo_term", "envo_uri", "envo_confidence", "envo_match_method",
        "proposed_concept_name", "proposed_action", "explanation"
    ]

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[done] Saved {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()