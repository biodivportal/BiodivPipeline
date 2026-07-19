#!/usr/bin/env python3
"""
evaluate.py - Evaluation script for WP5 ENVO matching and splitting
Compares match_envo() output against ground truth dataset
Calculates precision, recall, F-score, top-k accuracy and decision accuracy
Note: Splitting evaluation requires LLM API - disabled by default due to rate limits
"""

import csv
import json
import argparse
from pathlib import Path
from resolvers.locality.envo_matching import match_envo

# default paths
DATA_DIR = Path(__file__).parent / "data"
DEFAULT_GROUND_TRUTH_PATH = DATA_DIR / "provisional_concepts_ground_truth.csv"
DEFAULT_OUTPUT_PATH = DATA_DIR / "evaluation_results.json"

# score threshold for ENVO matching
SCORE_THRESHOLD = 0.82


def load_ground_truth(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    print(f"[info] Loaded {len(rows)} ground truth rows")
    return rows


def normalize_uri(uri):
    if not uri:
        return None
    return uri.strip().rstrip("/")


def get_top_match_uri(match_result):
    if not match_result or not match_result.get("exists", False):
        return None
    matches = match_result.get("matches", [])
    if not matches:
        return None
    return matches[0].get("iri", "")


def get_all_uris(match_result):
    if not match_result:
        return []
    matches = match_result.get("matches", [])
    return [m.get("iri") for m in matches if m.get("iri")]


def run_evaluation(ground_truth_path, output_path, enable_splitting=False):
    rows = load_ground_truth(ground_truth_path)

    # ENVO matching counters
    tp = fp = fn = tn = 0
    top1_correct = top3_correct = total_with_gt = 0

    # splitting counters
    location_correct = location_total = 0
    environment_correct = environment_total = 0

    # decision counters
    decision_correct_count = decision_total = 0

    results = []

    for i, row in enumerate(rows):
        original_term = row.get("original_term", "").strip()
        environment = row.get("split_environment", "").strip()
        ground_truth_uri = normalize_uri(row.get("matched_environment_envo_uri", ""))
        gt_location = row.get("split_location", "").strip()
        gt_environment = row.get("split_environment", "").strip()
        gt_decision = row.get("environment_decision", "REGISTER").strip()

        if not original_term:
            continue

        # splitting evaluation (disabled by default)
        pred_location = ""
        pred_environment = ""
        if enable_splitting:
            try:
                from resolvers.locality.cleaner import split_locality_label
                from rapidfuzz import fuzz
                import time
                time.sleep(5)
                split_result = split_locality_label([original_term])[0]
                pred_location = split_result.get("location", "").strip()
                pred_environment = split_result.get("environment", "").strip()

                if gt_location:
                    location_total += 1
                    if fuzz.token_sort_ratio(pred_location.lower(), gt_location.lower()) >= 80:
                        location_correct += 1

                if gt_environment:
                    environment_total += 1
                    if fuzz.token_sort_ratio(pred_environment.lower(), gt_environment.lower()) >= 80:
                        environment_correct += 1

            except Exception as e:
                print(f"[warn] Split failed for '{original_term[:50]}': {e}")

        # ENVO matching evaluation
        if not environment:
            our_decision = "REGISTER"
            decision_total += 1
            if our_decision == gt_decision:
                decision_correct_count += 1
            results.append({
                "original_term": original_term,
                "ground_truth_uri": None,
                "predicted_uri": None,
                "correct": not ground_truth_uri,
                "in_top1": False,
                "in_top3": False,
                "our_decision": our_decision,
                "gt_decision": gt_decision,
                "decision_correct": our_decision == gt_decision,
            })
            continue

        match_result = match_envo(environment)
        predicted_uri = normalize_uri(get_top_match_uri(match_result))
        all_uris = get_all_uris(match_result)

        in_top1 = in_top3 = False
        if ground_truth_uri:
            total_with_gt += 1
            if all_uris and all_uris[0] == ground_truth_uri:
                top1_correct += 1
                in_top1 = True
            if ground_truth_uri in all_uris:
                top3_correct += 1
                in_top3 = True

        if ground_truth_uri and predicted_uri:
            if ground_truth_uri == predicted_uri:
                tp += 1
                correct = True
            else:
                fp += 1
                correct = False
        elif ground_truth_uri and not predicted_uri:
            fn += 1
            correct = False
        elif not ground_truth_uri and predicted_uri:
            fp += 1
            correct = False
        else:
            tn += 1
            correct = True

        # decision evaluation
        our_decision = "ACCEPT" if predicted_uri else "REGISTER"
        decision_total += 1
        if our_decision == gt_decision:
            decision_correct_count += 1

        results.append({
            "original_term": original_term,
            "environment": environment,
            "ground_truth_uri": ground_truth_uri,
            "predicted_uri": predicted_uri,
            "correct": correct,
            "in_top1": in_top1,
            "in_top3": in_top3,
            "our_decision": our_decision,
            "gt_decision": gt_decision,
            "decision_correct": our_decision == gt_decision,
        })

        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(rows)} processed...")

    # calculate metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    top1_acc = top1_correct / total_with_gt if total_with_gt > 0 else 0
    top3_acc = top3_correct / total_with_gt if total_with_gt > 0 else 0
    location_acc = location_correct / location_total if location_total > 0 else 0
    environment_acc = environment_correct / environment_total if environment_total > 0 else 0
    decision_acc = decision_correct_count / decision_total if decision_total > 0 else 0

    print(f"\n--- ENVO Matching Results ---")
    print(f"True Positives:  {tp}")
    print(f"False Positives: {fp}")
    print(f"False Negatives: {fn}")
    print(f"True Negatives:  {tn}")
    print(f"Precision: {precision:.3f}")
    print(f"Recall:    {recall:.3f}")
    print(f"F-score:   {f_score:.3f}")
    print(f"\n--- Top-K Accuracy (rows with ground truth URI: {total_with_gt}) ---")
    print(f"Top-1 Accuracy: {top1_correct}/{total_with_gt} = {top1_acc:.1%}")
    print(f"Top-3 Accuracy: {top3_correct}/{total_with_gt} = {top3_acc:.1%}")
    print(f"\n--- Decision Evaluation ---")
    print(f"Decision accuracy: {decision_correct_count}/{decision_total} = {decision_acc:.1%}")
    print(f"\n--- Splitting Evaluation ---")
    if enable_splitting:
        print(f"Location accuracy:    {location_correct}/{location_total} = {location_acc:.1%}")
        print(f"Environment accuracy: {environment_correct}/{environment_total} = {environment_acc:.1%}")
    else:
        print(f"Splitting evaluation disabled (requires LLM API)")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "envo_precision": precision,
            "envo_recall": recall,
            "envo_f_score": f_score,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "top1_accuracy": top1_acc,
            "top3_accuracy": top3_acc,
            "decision_accuracy": decision_acc,
            "splitting_location_accuracy": location_acc,
            "splitting_environment_accuracy": environment_acc,
            "details": results
        }, f, indent=2, ensure_ascii=False)
    print(f"\n[done] Results saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate performance against ground truth")
    parser.add_argument("--ground-truth", default=DEFAULT_GROUND_TRUTH_PATH, help="Path to ground truth CSV")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, help="Path to output JSON")
    parser.add_argument("--enable-splitting", action="store_true", help="Enable splitting evaluation (requires LLM)")
    args = parser.parse_args()

    run_evaluation(
        ground_truth_path=args.ground_truth,
        output_path=args.output,
        enable_splitting=args.enable_splitting
    )


if __name__ == "__main__":
    main()
