#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from ingest import load_ontology_config, read_unresolved_csv
from resolvers.plant_taxons import score


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
    args = parser.parse_args()

    # data ingestion
    config = load_ontology_config(args.ontology_config)
    unresolved_rows = read_unresolved_csv(args.input)

    # score and match species
    match = [score(row, config) for row in unresolved_rows]

    # Emitting output for gbif scoring now
    output_data = {"provisional_concepts": match}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)


if __name__ == "__main__":
    main()
