import argparse
import csv
import json
import os
import time
import requests
from pathlib import Path
from deep_translator import GoogleTranslator

API_KEY = os.environ.get("BIODIV_API_KEY")
if not API_KEY:
    raise EnvironmentError("BIODIV_API_KEY environment variable not set")

# ---------------------------------------------------------------------------
# CLI arguments
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(
    description="Map CSV columns to ontologies via the GFBio recommender API."
)
parser.add_argument(
    "--csv",
    type=Path,
    default=Path("data/sample.csv"),
    metavar="PATH",
    help="Path to the input CSV file (default: data/sample.csv)",
)
parser.add_argument(
    "--output",
    type=Path,
    default=Path("modules/local/biodiv_annotate/bin/"),
    metavar="DIR",
    help="Directory where output files will be written (default: results/annotation/)",
)
args = parser.parse_args()

INPUT_FILE    = args.csv
OUTPUT_CSV    = args.output / "column_ontology_mapping.csv"
OUTPUT_CONFIG = args.output / "ontology_config.json"
OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------

SAMPLE_SIZE      = 50
THRESHOLD_USE    = 0.6   # above this -> pretty confidently use the ontology
THRESHOLD_REVIEW = 0.4   # between this and USE -> flag for manual review

# used this threshhold cause we theoretically never go over 0.7 cause of the recommender formula
# that calculates the scores 

RECOMMENDER_URL = "https://data.biodivportal.gfbio.org/recommender"

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

# German columns -> potential possible to translate to test another result
TRANSLATE_COLUMNS = {'''"Locality", "FundortUNdOeko", "Anmerkungen", "TitelEtikett", "Expeditionsangabe"'''}

translator = GoogleTranslator(source="auto", target="en")


def translate(text):
    try:
        return translator.translate(text) or text
    except Exception:
        return text


def sample_values(rows, col, n=SAMPLE_SIZE):
    # take rows and collect up to n non-empty values (no duplicates)
    seen, values = set(), []
    for row in rows:
        v = row.get(col, "").strip()
        if v and v not in seen:
            seen.add(v)
            values.append(v)
        if len(values) >= n:
            break
    return values


def build_input(rows, col, translated=False):
    values = sample_values(rows, col)
    if not values:
        return ""

    if translated and col in TRANSLATE_COLUMNS:
        values = [translate(v) for v in values]
   
    return ", ".join(values)

def query_recommender(text):
    try:
        resp = requests.get(
            RECOMMENDER_URL,
            params={"input": text, "output_type": "1"},
            headers={"Authorization": f"apikey token={API_KEY}"},
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  WARNING: API error: {e}")
        return []

    results = []
    for item in resp.json()[:5]:
        score = item.get("evaluationScore", 0.0)
        for onto in item.get("ontologies", []):
            acronym = onto.get("acronym", "")
            if acronym and len(results) < 5:
                results.append({
                    "acronym": acronym,
                    "name":    onto.get("name", ""),
                    "score":   round(score, 4),
                })
    
    print(results)
    
    return results


def decide(score):
    if score >= THRESHOLD_USE:
        return "use"
    if score >= THRESHOLD_REVIEW:
        return "review"
    return "skip"


def main():
    print(f"Reading {INPUT_FILE} ...")
    with open(INPUT_FILE, newline="", encoding="utf-8-sig") as f:
        reader  = csv.DictReader(f)
        rows    = list(reader)
        columns = reader.fieldnames or []
    print(f"Found {len(rows)} rows, {len(columns)} columns.\n")

    mapping_rows    = []
    ontology_config = {}

    for col in columns:

        # the skipped columns
        if col not in FIELDS_TO_CHECK:
            print(f"[SKIP]  {col}")
            mapping_rows.append({"column": col, "decision": "skip", "translation_used": "",
                "sample_text": "", "top_ontology_1": "", "score_1": "",
                "top_ontology_2": "", "score_2": "", "top_ontology_3": "", "score_3": ""})
            continue

        text = build_input(rows, col)

        # if column is empty
        if not text:
            print(f"[EMPTY] {col}")
            mapping_rows.append({"column": col, "decision": "skip", "translation_used": "",
                "sample_text": "", "top_ontology_1": "", "score_1": "",
                "top_ontology_2": "", "score_2": "", "top_ontology_3": "", "score_3": ""})
            continue

        print(f"[QUERY] {col}")
        print(f"  input: {text[:150]}{'...' if len(text) > 150 else ''}")

        results   = query_recommender(text)
        top       = results[0] if results else None
        top_score = top["score"] if top else 0.0
        trans_used = "no"
        time.sleep(0.5)

        # score too low (score < 0.6) -> try translation if translation could be useful and compare to german score
        if top_score < THRESHOLD_USE and col in TRANSLATE_COLUMNS:
            print(f"  score {top_score} < {THRESHOLD_USE} -> retrying with translation ...")
            results_en = query_recommender(build_input(rows, col, translated=True))
            top_en     = results_en[0] if results_en else None
            score_en   = top_en["score"] if top_en else 0.0
            if score_en > top_score:
                results, top, top_score = results_en, top_en, score_en
                trans_used = "yes (improved)"
                print(f"  improved to {top_score}")
            else:
                trans_used = "yes (no improvement)"
                print(f"  no improvement ({score_en} <= {top_score})")
            time.sleep(0.5)

        decision = decide(top_score) if top else "skip"
        print(f"  -> {top['acronym'] if top else 'none'} | score={top_score} | {decision}\n")

        row = {
            "column":           col,
            "decision":         decision,
            "translation_used": trans_used,
            "sample_text":      text[:300],
        }
        for i in range(3):
            idx = str(i + 1)
            row[f"top_ontology_{idx}"] = f"{results[i]['acronym']} - {results[i]['name']}" if i < len(results) else ""
            row[f"score_{idx}"]        = results[i]["score"] if i < len(results) else ""
        mapping_rows.append(row)

        if decision in ("use", "review") and top:
            ontology_config[col] = {
                "ontology":            top["acronym"],
                "name":                top["name"],
                "score":               top_score,
                "decision":            decision,
                "translation_used":    trans_used,
                "all_recommendations": results,
            }

    # ouput
    fieldnames = ["column", "decision", "translation_used", "sample_text",
                  "top_ontology_1", "score_1", "top_ontology_2", "score_2",
                  "top_ontology_3", "score_3"]

    '''
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(mapping_rows)
    '''

    with open(OUTPUT_CONFIG, "w", encoding="utf-8") as f:
        json.dump(ontology_config, f, indent=2, ensure_ascii=False)

    use    = sum(1 for r in mapping_rows if r["decision"] == "use")
    review = sum(1 for r in mapping_rows if r["decision"] == "review")
    skip   = sum(1 for r in mapping_rows if r["decision"] == "skip")
    print(f"Done. {use} use / {review} review / {skip} skip")
    print(f"Outputs: {OUTPUT_CSV}, {OUTPUT_CONFIG}")


if __name__ == "__main__":
    main()