import os
import csv
import json
import time
import requests
from dotenv import load_dotenv
import unicodedata
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

def get_api_key():
    api_key = os.environ.get("BIODIV_API_KEY") 
    if not api_key:
        raise ValueError("Missing BIODIV_API_KEY")
    return api_key

API_URL = "https://data.biodivportal.gfbio.org/annotator"

INPUT_CSV = "data/sample.csv"
OUT_JSON = "results/annotation/annotated.jsonld"
OUT_UNRESOLVED = "results/annotation/unresolved_terms.csv"
OUT_ENRICHED_CSV = "results/annotation/enriched.csv"
OUT_UNRESOLVED_WP5 = "results/annotation/unresolved_rows_for_wp5.csv"



# prevents crash if results folder does not exist
os.makedirs("results/annotation", exist_ok=True)


MAX_ROWS = 100000
WAIT_BETWEEN_REQUESTS = 0
MAX_WORKERS = 10


ONTOLOGY_CONFIG_PATH = "modules/local/biodiv_annotate/bin/ontology_config.json"

def load_ontology_config(path):
    # load recommender output.sjon and build a field -> ontology mapping
    # only using fields "use" and "review" and if "skip" we use no filter (gotta discuss that)
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        print(f"[warn] Ontology config not found at {path!r}, annotating without ontology filter.", flush=True)
        return {}

    mapping = {}
    for field, cfg in raw.items():
        ontology = cfg.get("ontology")
        decision = cfg.get("decision", "use")
        if ontology and decision != "skip":
            mapping[field] = ontology or None

    return mapping



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
    "Expeditionsangabe",
    # "Anmerkungen",
]

def get_ontology_name(url):
    # Ontology links end with the ontology acronym ex: NCBITAXON
    if not url:
        return ""
    return url.rstrip("/").split("/")[-1]

def ask_annotator(text, ontology=None, retries=3):
    # send one text value to BiodivPortal Annotator
    # The response is JSON-LD, but we can read it like normal JSON
    # retry because the API can sometimes timeout
    params = {
        "text": text,
        "apikey": API_KEY,
        "whole_word_only": "true",
        "exclude_numbers": "true",
    }

    if ontology:
        params["ontologies"] = ontology

    last_error = None

    for attempt in range(retries):
        try:
            res = requests.get(API_URL, params=params, timeout=30)
            res.raise_for_status()

            try:
                return res.json()
            except ValueError as e:
                raise RuntimeError(f"Invalid JSON response from API: {e}")

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
    # utf-8-sig avoids problems with BOM in the CSV header
    rows = []

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader):
            if i >= limit:
                break
            rows.append(row)

    return rows


def normalize_term(value):
# Normalize the term before sending to the API    
    if not value:
        return ""

    value = str(value).strip()
    value = unicodedata.normalize("NFKC", value)
    value = " ".join(value.split())

    return value


def annotate_term(term, api_key, ontology=None):    
# Annotate a single unique term via the BiodivPortal API
# Returns the annotation result or error information
    try:
        api_result = ask_annotator(term, ontology=ontology)

        result = {
            "term": term,
            "api_result": api_result,
            "ontology_filter": ontology,
        }

    # If the API request fails, we keep the term in unresolved output
    # instead of stopping the whole run
    except requests.RequestException as e:
        result = {
            "term": term,
            "api_result": [],
            "error": f"api_error: {e}",
            "ontology_filter": ontology,
        }    

    except Exception as e:
        result = {
            "term": term,
            "api_result": [],
            "error": f"unexpected_error: {e}",
            "ontology_filter": ontology,
        }

    time.sleep(WAIT_BETWEEN_REQUESTS)

    return result

def collect_terms(rows):
# Collect unique terms from specified fields across all records, and keep track of where they occur for later annotation    
    terms = {}

    for row in rows:
        record_id = row.get("HerbariumID")


        for field in FIELDS_TO_CHECK:
            raw_value = row.get(field, "")
            value = normalize_term(row.get(field, ""))

            if not value:
                continue

            key = f"{field}::{value.lower()}"

            if key not in terms:
                terms[key] = {
                    "term": value,
                    "occurrences": [],
                }

            terms[key]["occurrences"].append({
                "record_id": record_id,
                "source_field": field,
                "original_term": raw_value,
                "normalized_term": value,
            })

    return terms

# ---- Optional parallel version for larger datasets: ----
def annotate_unique_terms(terms, api_key):
    # Annotate unique terms in parallel
    results = {}
    total = len(terms)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_key = {
            executor.submit(
                annotate_term,
                data["term"],
                api_key,
                # derive field name from the "field::value" key
                FIELD_ONTOLOGY.get(key.split("::")[0]),
            ): key
            for key, data in terms.items()
        }

        for index, future in enumerate(as_completed(future_to_key), start=1):
            key = future_to_key[future]
            term = terms[key]["term"]

            print(
                f"[{index}/{total}] Finished annotating term: {term}",
                flush=True
            )

            results[key] = future.result()

    return results

def count_unique_unresolved(rows):
    return len({
        (normalize_term(row["term"]).lower(), row["reason"])
        for row in rows
    })
# improving unresolved_terms.csv output 
def guess_category(field):
    if field in ["FullNameCache", "NameCache", "Genus", "Family"]:
        return "taxon"
    if field in ["Country", "Locality"]:
        return "location"
    if field == "FundortUNdOeko":
        return "ecology_or_habitat"
    if field in ["TitelEtikett", "Expeditionsangabe"]:
        return "expedition_or_note"
    return "unknown"



def annotate_records(rows, terms, term_results):
    row_lookup = {row["HerbariumID"]: row for row in rows}

    records = {}
    unresolved = []
    wp5_by_record = {}

    for row in rows:
        record_id = row.get("HerbariumID")

        records[record_id] = {
            "record_id": record_id,
            "source_fields": {},
            "annotation_count": 0,
            "annotations": [],
        }

    for key, data in terms.items():
        term = data["term"]
        result = term_results[key]

        for occurrence in data["occurrences"]:
            record_id = occurrence["record_id"]
            field = occurrence["source_field"]
            row = row_lookup.get(record_id, {})

            records[record_id]["source_fields"][field] = term

            parsed = simplify_response(result["api_result"], field)

            if len(parsed) == 0:
                reason = result.get("error", "no_annotation_returned")
                original_term = occurrence.get("original_term", term)
                normalized_term = occurrence.get("normalized_term", term)
                ontology_filter = result.get("ontology_filter", "")
                suggested_category = guess_category(field)

                unresolved.append({
                    "record_id": record_id,
                    "source_field": field,
                    "original_term": original_term,
                    "normalized_term": normalized_term,
                    "term": term,
                    "reason": reason,
                    "ontology_filter": ontology_filter,
                    "suggested_category": suggested_category,
                    "row_context": row,

                    "example_FullNameCache": row.get("FullNameCache", ""),
                    "example_NameCache": row.get("NameCache", ""),
                    "example_Genus": row.get("Genus", ""),
                    "example_Family": row.get("Family", ""),
                    "example_Country": row.get("Country", ""),
                    "example_Locality": row.get("Locality", ""),
                    "example_FundortUNdOeko": row.get("FundortUNdOeko", ""),
                    "example_TitelEtikett": row.get("TitelEtikett", ""),
                    "example_Expeditionsangabe": row.get("Expeditionsangabe", ""),
                })

                wp5_by_record.setdefault(record_id, []).append({
                    "source_field": field,
                    "original_term": occurrence.get("original_term", term),
                    "normalized_term": occurrence.get("normalized_term", term),
                    "ontology_filter": result.get("ontology_filter", ""),
                })

                continue

            records[record_id]["annotations"].extend(parsed)

    final_records = []

    for record in records.values():
        deduplicated = remove_duplicates(record["annotations"])
        record["annotations"] = deduplicated
        record["annotation_count"] = len(deduplicated)
        final_records.append(record)

    unresolved_rows_for_wp5 = []

    for record_id, unresolved_items in wp5_by_record.items():
        row = dict(row_lookup[record_id])

        failed_fields = list(dict.fromkeys(item["source_field"] for item in unresolved_items))
        row["unresolved_fields"] = ", ".join(failed_fields)

        unresolved_rows_for_wp5.append(row)

    return final_records, unresolved, unresolved_rows_for_wp5



def save_json(records):
    output = {
        "@context": {
            "record_id": "https://schema.org/identifier",
            "source_fields": "https://schema.org/additionalProperty",
            "annotations": "https://schema.org/about",
            "matched_text": "https://schema.org/name",
            "source_field": "https://schema.org/propertyID",
            "match_type": "https://schema.org/additionalType",
            "class_id": "@id",
            "ontology": "https://schema.org/isPartOf",
            "ontology_url": "https://schema.org/url",
            "ui_link": "https://schema.org/url",
            "suspicious_short_match": "https://schema.org/Boolean",
        },
        "@graph": records,
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


def save_unresolved(rows):
    aggregated = {}

    for row in rows:
        key = (
            row["source_field"],
            normalize_term(row["normalized_term"]).lower(),
            row["reason"],
            # "suggested_category": guess_category(field),
            # "row_context": row,
        )

        if key not in aggregated:
            aggregated[key] = {
        "source_field": row["source_field"],
        "original_term": row["original_term"],
        "normalized_term": row["normalized_term"],
        "suggested_category": row.get("suggested_category", ""),
        "reason": row["reason"],
        "ontology_filter": row.get("ontology_filter", ""),
        "count": 0,
        "record_ids": set(),

        "example_FullNameCache": row.get("example_FullNameCache", ""),
        "example_NameCache": row.get("example_NameCache", ""),
        "example_Genus": row.get("example_Genus", ""),
        "example_Family": row.get("example_Family", ""),
        "example_Country": row.get("example_Country", ""),
        "example_Locality": row.get("example_Locality", ""),
        "example_FundortUNdOeko": row.get("example_FundortUNdOeko", ""),
        "example_TitelEtikett": row.get("example_TitelEtikett", ""),
        "example_Expeditionsangabe": row.get("example_Expeditionsangabe", ""),
}

        aggregated[key]["count"] += 1
        aggregated[key]["record_ids"].add(row["record_id"])
        # aggregated[key]["source_fields"].add(row["source_field"])

    with open(OUT_UNRESOLVED, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "source_field",
                "original_term",
                "normalized_term",
                "suggested_category",
                "reason",
                "ontology_filter",
                "count",
                "record_ids",
                "example_FullNameCache",
                "example_NameCache",
                "example_Genus",
                "example_Family",
                "example_Country",
                "example_Locality",
                "example_FundortUNdOeko",
                "example_TitelEtikett",
                "example_Expeditionsangabe",
            ]
        )

        writer.writeheader()

        for item in aggregated.values():
            item["record_ids"] = "|".join(sorted(item["record_ids"]))
            # item["source_fields"] = "|".join(sorted(item["source_fields"]))

            writer.writerow(item)

def save_enriched_csv(rows, annotated_records, out_path):
    if not rows:
        return

    # Build lookup: record_id -> {field: first_uri}
    uri_lookup = {}
    for record in annotated_records:
        record_id = record["record_id"]
        field_uri = {}
        for ann in record["annotations"]:
            field = ann["source_field"]
            if field not in field_uri and ann.get("class_id"):
                field_uri[field] = ann["class_id"]
        uri_lookup[record_id] = field_uri

    # Building output columns: insert _URI right after each annotated field
    original_fields = list(rows[0].keys())
    output_fields = []
    for col in original_fields:
        output_fields.append(col)
        if col in FIELDS_TO_CHECK:
            output_fields.append(f"{col}_URI")

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=output_fields)
        writer.writeheader()

        for row in rows:
            record_id = row.get("HerbariumID")
            uris = uri_lookup.get(record_id, {})
            out_row = dict(row)
            for field in FIELDS_TO_CHECK:
                if field in original_fields:
                    out_row[f"{field}_URI"] = uris.get(field, "")
            writer.writerow(out_row)

def save_unresolved_rows_for_wp5(rows, output_path):
    if not rows:
        return

    fieldnames = list(rows[0].keys())

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def parse_target_ontologies(items):
    if not items:
        return {}

    mapping = {}

    for item in items:
        if ":" not in item:
            raise ValueError(
                f"Invalid ontology mapping {item!r}. "
                "Expected format COLUMN:ONTOLOGY"
            )

        column, ontology = item.split(":", 1)
        column = column.strip()
        ontology = ontology.strip()

        if not column or not ontology:
            raise ValueError(
                f"Invalid ontology mapping {item!r}. "
                "Column and ontology must not be empty."
            )

        mapping[column] = ontology

    return mapping

def parse_args():
    parser = argparse.ArgumentParser(description="Annotate biodiversity CSV records with BiodivPortal.")
    parser.add_argument("--input", default=INPUT_CSV)
    parser.add_argument("--out-json", default=OUT_JSON)
    parser.add_argument("--out-unresolved", default=OUT_UNRESOLVED)
    parser.add_argument("--out-wp5-unresolved-rows", default=OUT_UNRESOLVED_WP5)
    parser.add_argument("--out-enriched-csv", default="results/annotation/enriched.csv")
    parser.add_argument("--max-rows", type=int, default=MAX_ROWS)
    parser.add_argument("--columns", nargs="+", default=FIELDS_TO_CHECK)
    parser.add_argument("--target-ontologies", dest="target_ontologies", nargs="+",default=None)
    return parser.parse_args()

# if __name__ == "__main__":
#     start_time = time.perf_counter()

#     rows = read_rows(INPUT_CSV, MAX_ROWS)
if __name__ == "__main__":
    args = parse_args()

    API_KEY = get_api_key()

    INPUT_CSV = args.input
    OUT_JSON = args.out_json
    OUT_UNRESOLVED = args.out_unresolved
    OUT_UNRESOLVED_WP5 = args.out_wp5_unresolved_rows
    MAX_ROWS = args.max_rows
    FIELDS_TO_CHECK = args.columns
    FIELD_ONTOLOGY = load_ontology_config(ONTOLOGY_CONFIG_PATH)
    cli_ontologies = parse_target_ontologies(args.target_ontologies)
    FIELD_ONTOLOGY.update(cli_ontologies)

    for field in FIELDS_TO_CHECK:
        ontology = FIELD_ONTOLOGY.get(field)
        if not ontology:
            print(
                f"[warn] No ontology configured for column {field!r}; "
                "annotating without ontology filter.", flush=True,)
        
    # os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    # os.makedirs(os.path.dirname(OUT_UNRESOLVED), exist_ok=True)

    out_json_dir = os.path.dirname(OUT_JSON)
    out_unresolved_dir = os.path.dirname(OUT_UNRESOLVED)
    out_unresolved_for_wp5 = os.path.dirname(OUT_UNRESOLVED_WP5)

    if out_unresolved_for_wp5:
        os.makedirs(out_unresolved_for_wp5, exist_ok=True)

    if out_json_dir:
        os.makedirs(out_json_dir, exist_ok=True)

    if out_unresolved_dir:
        os.makedirs(out_unresolved_dir, exist_ok=True)

    start_time = time.perf_counter()

    rows = read_rows(INPUT_CSV, MAX_ROWS)

    terms = collect_terms(rows)
    term_results = annotate_unique_terms(terms, API_KEY)

    print("Building annotated records...", flush=True)

    annotate_start = time.perf_counter()
    annotated, unresolved_terms, unresolved_rows_for_wp5 = annotate_records(
    rows,
    terms,
    term_results,
)
    annotate_time = time.perf_counter() - annotate_start

    save_start = time.perf_counter()

    print("Writing annotated JSON-LD...", flush=True)
    save_json(annotated)

    # print("Writing Unresolved CSV...", flush=True)
    # save_unresolved(unresolved_terms)

    print("Writing unresolved rows to unresolved_terms.csv...", flush=True)
    save_unresolved_rows_for_wp5(
        unresolved_rows_for_wp5,
        OUT_UNRESOLVED,
    )
    print("Saved:", OUT_UNRESOLVED)

    OUT_ENRICHED_CSV = args.out_enriched_csv

    out_enriched_dir = os.path.dirname(OUT_ENRICHED_CSV)
    if out_enriched_dir:
        os.makedirs(out_enriched_dir, exist_ok=True)

    print("Writing enriched CSV...", flush=True)
    save_enriched_csv(rows, annotated, OUT_ENRICHED_CSV)
    print("Saved:", OUT_ENRICHED_CSV)

    save_time = time.perf_counter() - save_start

    total_annotations = sum(
        item.get("annotation_count", 0)
        for item in annotated
    )

    runtime = time.perf_counter() - start_time
    minutes = int(runtime // 60)
    seconds = runtime % 60

    print()
    print("Processed records:", len(annotated))
    print("Total annotations:", total_annotations)
    print("Unresolved occurrences:", len(unresolved_terms))
    print("Unresolved terms:", count_unique_unresolved(unresolved_terms))
    print("Saved:", OUT_JSON)
    print("Saved:", OUT_UNRESOLVED)
    print(f"Annotation processing time: {annotate_time:.2f}s")
    print(f"Runtime: {minutes}m {seconds:.2f}s")
    print(f"Saving time: {save_time:.2f}s")
