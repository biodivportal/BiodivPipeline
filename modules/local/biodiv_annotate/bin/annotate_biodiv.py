import os
import csv
import json
import time
import requests
from dotenv import load_dotenv

# small WP2 prototype:
# read a few biodiversity records, call BiodivPortal Annotator,
# and save simplified annotation results

load_dotenv()

API_KEY = os.getenv("BIODIV_API_KEY")

if not API_KEY:
    raise RuntimeError("BIODIV_API_KEY is missing. Please add it to your .env file.")

API_URL = "https://data.biodivportal.gfbio.org/annotator"

INPUT_CSV = "test_data/sample.csv"
OUT_JSON = "results/annotation/annotated.jsonld"
OUT_UNRESOLVED = "results/annotation/unresolved_terms.csv"

MAX_ROWS = 5
WAIT_BETWEEN_REQUESTS = 0.5

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
    if not url:
        return ""
    return url.rstrip("/").split("/")[-1]


def ask_annotator(text):
    params = {
        "text": text,
        "apikey": API_KEY,
        "whole_word_only": "true",
        "exclude_numbers": "true",
    }

    res = requests.get(API_URL, params=params, timeout=30)
    res.raise_for_status()
    return res.json()


def simplify_response(api_result, field_name):
    annotations = []

    for item in api_result:
        cls = item.get("annotatedClass", {})
        links = cls.get("links", {})

        class_id = cls.get("@id")
        ontology_url = links.get("ontology")
        ontology = get_ontology_name(ontology_url)

        for hit in item.get("annotations", []):
            text = hit.get("text", "")

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
    result = []
    seen = set()

    for ann in annotations:
        key = (ann["matched_text"], ann["class_id"], ann["ontology"])

        if key not in seen:
            result.append(ann)
            seen.add(key)

    return result


def read_rows(path, limit):
    rows = []

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader):
            if i >= limit:
                break
            rows.append(row)

    return rows


def annotate_record(row):
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

            if len(parsed) == 0:
                unresolved.append({
                    "record_id": record_id,
                    "source_field": field,
                    "term": value,
                    "reason": "no_annotation_returned",
                })

            all_annotations.extend(parsed)

        except requests.RequestException as e:
            unresolved.append({
                "record_id": record_id,
                "source_field": field,
                "term": value,
                "reason": f"api_error: {e}",
            })

        time.sleep(WAIT_BETWEEN_REQUESTS)

    all_annotations = remove_duplicates(all_annotations)

    enriched = {
        "record_id": record_id,
        "source_fields": used_fields,
        "annotation_count": len(all_annotations),
        "annotations": all_annotations,
    }

    return enriched, unresolved


def save_json(records):
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def save_unresolved(rows):
    with open(OUT_UNRESOLVED, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["record_id", "source_field", "term", "reason"])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    rows = read_rows(INPUT_CSV, MAX_ROWS)

    annotated = []
    unresolved_terms = []

    for row in rows:
        print("Annotating:", row.get("HerbariumID"))

        result, unresolved = annotate_record(row)
        annotated.append(result)
        unresolved_terms.extend(unresolved)

    save_json(annotated)
    save_unresolved(unresolved_terms)

    total_annotations = sum(item["annotation_count"] for item in annotated)

    print()
    print("Processed records:", len(annotated))
    print("Total annotations:", total_annotations)
    print("Unresolved terms:", len(unresolved_terms))
    print("Saved:", OUT_JSON)
    print("Saved:", OUT_UNRESOLVED)
    