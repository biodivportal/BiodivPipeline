import csv
import json
import os

def load_ontology_config(config_path):
    """Reads the ontology config JSON file."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading ontology config: {e}")
        return {}

def read_unresolved_csv(csv_path):
    """Reads the unresolved CSV file."""
    try:
        with open(csv_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        print(f"Error reading unresolved CSV: {e}")
        return []
