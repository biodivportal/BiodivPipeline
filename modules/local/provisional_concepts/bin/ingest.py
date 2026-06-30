import csv
import json


def load_ontology_config(config_path):
    """Reads the ontology config JSON file."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading ontology config: {e}")
        return {}


def read_unresolved_csv(csv_path, allowed_fields=None):
    """Reads the unresolved CSV file, keeping whitelisted fields and ignoring stop list"""

    if allowed_fields is None:
        allowed_fields = {
            "NameCache",
            "Genus",
            "FullNameCache",
            "Family",
            "Locality",
            "FundortUNdOeko",
        }
    else:
        allowed_fields = set(allowed_fields)

    # This should likely be changed, a stop word in only one column should not ommit the whole row
    stoplist = [
        "keine",
        "indet.",
        "!indet.",
    ]

    filtered_rows = []

    try:
        with open(csv_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                source_field = row.get("source_field", "").strip()
                original_term = row.get("original_term", "").strip()

                if source_field in allowed_fields and original_term not in stoplist:
                    filtered_rows.append(row)
            return filtered_rows

    except Exception as e:
        print(f"Error reading unresolved CSV: {e}")
        return []
