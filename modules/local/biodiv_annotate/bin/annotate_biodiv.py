import os
import csv
import json
import time
import argparse
import requests
from dotenv import load_dotenv

# WP2 Sprint 0 prototype
# for now this script only tests the BiodivPortal Annotator on a few sample rows.

load_dotenv()

# API key is kept in .env, so we do not hardcode it in the script
API_KEY = os.getenv("BIODIV_API_KEY")

if not API_KEY:
    raise RuntimeError("BIODIV_API_KEY is missing. Please add it to your .env file.")

API_URL = "https://data.biodivportal.gfbio.org/annotator"

DEFAULT_INPUT_CSV = "test_data/Belege_aus_D.csv"
DEFAULT_OUT_JSON = "results/annotation/annotated.jsonld"
DEFAULT_OUT_UNRESOLVED = "results/annotation/unresolved_terms.csv"

DEFAULT_MAX_ROWS = 20
WAIT_BETWEEN_REQUESTS = 0.5


# columns contain the most useful text for ontology annotation
# technical fields like image links, etc are skipped for now
FIELDS_TO_CHECK = [
    "FullNameCache",
    "NameCache",
    "Genus",
    "Family",
    "Locality",
    "FundortUNdOeko",
    "Country",
    "TitelEtikett",
]


def get_ontology_name(url):
    # Ontology links end with the ontology acronym ex: NCBITAXON
    if not url:
        return ""
    return url.rstrip("/").split("/")[-1]


def ask_annotator(text, retries=3):
    params = {
        "text": text,
        "apikey": API_KEY,
        "whole_word_only": "true",
        "exclude_numbers": "true",
    }

    last_error = None

    for attempt in range(retries):
        try:
            res = requests.get(API_URL, params=params, timeout=30)
            res.raise_for_status()
            return res.json()

        except requests.RequestException as e:
            last_error = e

            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))

    raise last_error


def simplify_response(api_result, field_name):
    # The API returns a large nested response
    # Here we keep only the parts that are useful for the next pipeline steps
    annotations = []

    for item in api_result:
        cls = item.get("annotatedClass", {})
        links = cls.get("links", {})

        class_id = cls.get("@id")
        ontology_url = links.get("ontology")
        ontology = get_ontology_name(ontology_url)

        for hit in item.get("annotations", []):
            text = hit.get("text", "")

            # if text and len(text) <= 3:
            #     continue

            annotations.append({
                "source_field": field_name,
                "matched_text": text,
                "match_type": hit.get("matchType"),
                "from": hit.get("from"),
                "to": hit.get("to"),
                "class_id": class_id,
                "ontology": ontology,
                "ontology_url": ontology_url,
                "ui_link": links.get("ui"),
                "suspicious_short_match": len(text) <= 3 if text else False,
            })

    return annotations


def remove_duplicates(annotations):
    # The same concept can appear from several fields, for example genus/name.
    # This keeps only one copy of the same matched text + ontology class.
    result = []
    seen = set()

    for ann in annotations:
        key = (ann["matched_text"], ann["class_id"], ann["ontology"])

        if key not in seen:
            result.append(ann)
            seen.add(key)

    return result


def read_rows(path, limit):
    # utf-8-sig avoids problems with BOM (Byte Order Mark) in the CSV header
    rows = []

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader):
            if i >= limit:
                break
            rows.append(row)

    return rows


def annotate_record(row):
     # Each CSV row becomes one enriched biodiversity record
    record_id = row.get("HerbariumID")
    all_annotations = []
    unresolved = []
    used_fields = {}

    for field in FIELDS_TO_CHECK:
        value = row.get(field, "")

        if not value:
            continue

        value = value.strip()

        if not value:
            continue

        used_fields[field] = value

        try:
            api_result = ask_annotator(value)
            parsed = simplify_response(api_result, field)


            # Empty API result means WP2 could not resolve this field
            # These terms can later be useful for WP5
            if len(parsed) == 0:
                unresolved.append({
                    "record_id": record_id,
                    "source_field": field,
                    "term": value,
                    "reason": "no_annotation_returned",
                })

            all_annotations.extend(parsed)

        except requests.RequestException as e:
            # If the API request fails, we keep the term in unresolved output
            # instead of stopping the whole run.
            unresolved.append({
                "record_id": record_id,
                "source_field": field,
                "term": value,
                "reason": f"api_error: {e}",
            })

        time.sleep(WAIT_BETWEEN_REQUESTS)   # Small pause to avoid sending requests too aggressively.


    all_annotations = remove_duplicates(all_annotations)

    # final enriched biodiversity record
    enriched = {
        "record_id": record_id,
        "source_fields": used_fields,
        "annotation_count": len(all_annotations),
        "annotations": all_annotations,
    }

    return enriched, unresolved


def save_json(records, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def save_unresolved(rows, output_path):
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["record_id", "source_field", "term", "reason"])
        writer.writeheader()
        writer.writerows(rows)


def get_args():
    parser = argparse.ArgumentParser(description="WP2 BiodivPortal annotation prototype")

    parser.add_argument("--input", default=DEFAULT_INPUT_CSV)
    parser.add_argument("--out-json", default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-unresolved", default=DEFAULT_OUT_UNRESOLVED)
    parser.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS)

    return parser.parse_args()    

if __name__ == "__main__":
    args = get_args()

    rows = read_rows(args.input, args.max_rows)

    annotated = []
    unresolved_terms = []

    for row in rows:
        print("Annotating:", row.get("HerbariumID"))

        result, unresolved = annotate_record(row)
        annotated.append(result)
        unresolved_terms.extend(unresolved)

  
    save_json(annotated, args.out_json)
    save_unresolved(unresolved_terms, args.out_unresolved)

    total_annotations = sum(item["annotation_count"] for item in annotated)

    print()
    print("Processed records:", len(annotated))
    print("Total annotations:", total_annotations)
    print("Unresolved terms:", len(unresolved_terms))
    print("Saved:", args.out_json)
    print("Saved:", args.out_unresolved)    