#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from ingest import load_ontology_config, read_unresolved_csv
from resolvers.plant_taxons import score as score_taxon
from resolvers.locality import score as score_locality


def main():
    default_ontology_config = Path(__file__).parent / "ontology_config.json"

    parser = argparse.ArgumentParser(
        description="Ingest unresolved terms and ontology config."
    )
    parser.add_argument("--input", required=True, help="Path to input unresolved CSV")
    parser.add_argument("--output", required=True, help="Path to output JSON")
    parser.add_argument(
        "--ontology-config",
        default=default_ontology_config,
        help="Path to ontology config JSON",
    )
    parser.add_argument(
        "--allowed-fields",
        nargs="*",
        help="Space-separated list of whitelisted columns to process",
    )
    parser.add_argument(
        "--species",
        action="store_true",
        help="Process taxonomic/species columns",
    )
    parser.add_argument(
        "--localities",
        action="store_true",
        help="Process geographic/locality columns",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit the number of rows processed",
    )
    args = parser.parse_args()

    allowed_fields = None
    if args.allowed_fields is not None:
        allowed_fields = set(args.allowed_fields)

    if args.species or args.localities:
        if allowed_fields is None:
            allowed_fields = set()
        if args.species:
            allowed_fields.update({"NameCache", "Genus", "FullNameCache", "Family"})
        if args.localities:
            allowed_fields.update({"Locality", "FundortUNdOeko"})

    # data ingestion
    config = load_ontology_config(args.ontology_config)
    unresolved_rows = read_unresolved_csv(args.input, allowed_fields=allowed_fields)
    if args.limit is not None:
        unresolved_rows = unresolved_rows[:args.limit]

    # score and match records (species vs environment/locality)
    taxon_fields = {"NameCache", "Genus", "FullNameCache", "Family"}
    locality_fields = {"Locality", "FundortUNdOeko"}

    match = []
    for row in unresolved_rows:
        sf = row.get("source_field")
        if sf in taxon_fields:
            match.append(score_taxon(row, config))
        elif sf in locality_fields:
            match.append(score_locality(row, config))

    # Emitting output for gbif scoring now
    output_data = {"provisional_concepts": match}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
