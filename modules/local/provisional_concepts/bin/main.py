#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from ingest import load_ontology_config, read_unresolved_csv, resolve_mapping, split_resolvers
from resolvers.plant_taxons import score as score_taxon
from resolvers.locality import score as score_locality


def parse_args():
    parser = argparse.ArgumentParser(description="Resolve provisional concepts from a CSV.")
    parser.add_argument("--input", required=True, help="Path to input CSV")
    parser.add_argument("--output", required=True, help="Path to output JSON")
    parser.add_argument(
        "--ontology-config",
        default=Path(__file__).parent / "ontology_config.json",
        help="Path to ontology config JSON",
    )
    parser.add_argument("--limit", type=int, help="Limit the number of rows processed")
    parser.add_argument("--mapping", help="JSON file with column mappings (overrides defaults)")
    parser.add_argument("--id-col")
    parser.add_argument("--unresolved-terms-col")
    parser.add_argument("--family-col")
    parser.add_argument("--genus-col")
    parser.add_argument("--name-col")
    parser.add_argument("--fullname-col")
    parser.add_argument("--locality-col", nargs="*")
    parser.add_argument("--country-col")
    parser.add_argument("--skip-species", action="store_true", help="Skip resolving plant taxons/species")
    parser.add_argument("--skip-localities", action="store_true", help="Skip resolving localities/environments")
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_ontology_config(args.ontology_config)
    mapping = resolve_mapping(args)
    records = read_unresolved_csv(args.input, mapping, args.limit)

    taxon_rows, locality_rows = split_resolvers(records)

    match = []
    if not args.skip_species:
        match.extend([score_taxon(r, config) for r in taxon_rows])
    if not args.skip_localities:
        match.extend(score_locality(locality_rows, config))

    for m in match:
        if isinstance(m.get("unresolved_terms"), list):
            m["unresolved_terms"] = ", ".join(m["unresolved_terms"])

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"provisional_concepts": match}, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
