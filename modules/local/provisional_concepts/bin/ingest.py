import csv
import json

TAXON_FIELDS = {"Family", "Genus", "NameCache", "FullNameCache"}
LOCALITY_FIELDS = {"Locality", "FundortUNdOeko"}
FIELD_TO_KEY = {
    "Family": "family",
    "Genus": "genus",
    "NameCache": "name",
    "FullNameCache": "fullname",
}


def resolve_mapping(args):
    """Resolves column mapping, layering CLI overrides on top of defaults and custom JSON configurations."""
    # Default mappings (based on WP2 output)
    mapping = {
        "id": "HerbariumID",
        "unresolved_terms": "unresolved_fields",
        "family_column": "Family",
        "genus_column": "Genus",
        "name_column": "NameCache",
        "fullname_column": "FullNameCache",
        "locality_column": ["Locality", "FundortUNdOeko"],
        "country_column": "Country",
    }

    if getattr(args, "mapping", None):
        with open(args.mapping, encoding="utf-8") as f:
            mapping.update(json.load(f))

    if getattr(args, "id_col", None):
        mapping["id"] = args.id_col
    if getattr(args, "unresolved_terms_col", None):
        mapping["unresolved_terms"] = args.unresolved_terms_col
    if getattr(args, "family_col", None):
        mapping["family_column"] = args.family_col
    if getattr(args, "genus_col", None):
        mapping["genus_column"] = args.genus_col
    if getattr(args, "name_col", None):
        mapping["name_column"] = args.name_col
    if getattr(args, "fullname_col", None):
        mapping["fullname_column"] = args.fullname_col
    if getattr(args, "locality_col", None):
        mapping["locality_column"] = args.locality_col
    return mapping


def load_ontology_config(config_path):
    """Reads the ontology config JSON file."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading ontology config: {e}")
        return {}


def read_unresolved_csv(csv_path, mapping, limit=None):
    """Read a CSV into one record dict per row, picking columns via `mapping`.
    """
    id_col = mapping["id"]
    unresolved_col = mapping.get("unresolved_terms")
    locality_cols = mapping["locality_column"]
    if not isinstance(locality_cols, list):
        locality_cols = [locality_cols]

    records = []
    try:
        with open(csv_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if limit is not None and i >= limit:
                    break

                unresolved_val = row.get(unresolved_col) or "" if unresolved_col else ""
                unresolved_terms = [f.strip() for f in unresolved_val.split(",") if f.strip()]

                family = (row.get(mapping["family_column"]) or "").strip()
                genus = (row.get(mapping["genus_column"]) or "").strip()
                name = (row.get(mapping["name_column"]) or "").strip()
                fullname = (row.get(mapping["fullname_column"]) or "").strip()

                locality = [(row.get(col) or "").strip() for col in locality_cols]

                records.append(
                    {
                        "id": (row.get(id_col) or "").strip(),
                        "unresolved_terms": unresolved_terms,
                        "family": family,
                        "genus": genus,
                        "name": name,
                        "fullname": fullname,
                        "locality": locality,
                        "row": row,
                    }
                )
    except Exception as e:
        print(f"Error reading CSV: {e}")
    return records


def split_resolvers(records):
    taxon_rows = []
    locality_rows = []

    for rec in records:
        fields = rec.get("unresolved_terms")
        if not fields:
            taxon_rows.append(rec)
            locality_rows.append(rec)
            continue

        if any(f in TAXON_FIELDS for f in fields):
            taxon_rows.append(rec)
        if any(f in LOCALITY_FIELDS for f in fields):
            locality_rows.append(rec)

    return taxon_rows, locality_rows
