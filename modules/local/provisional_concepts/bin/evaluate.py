#!/usr/bin/env python3
"""
evaluate.py - Evaluation script for WP5 ENVO matching
Compares match_envo() output against ground truth dataset
Calculates precision, recall, F-score and top-k accuracy
"""

import csv
import json
from pathlib import Path
from resolvers.locality.envo_matching import match_envo

# paths
DATA_DIR = Path(__file__).parent / "data"
GROUND_TRUTH_PATH = DATA_DIR / "provisional_concepts_ground_truth.csv"

# score threshold - only accept matches above this
SCORE_THRESHOLD = 0.82


def load_ground_truth(path):
    # load ground truth csv
    rows = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    print(f"[info] Loaded {len(rows)} ground truth rows")
    return rows


def normalize_uri(uri):
    # normalize URI for comparison
    if not uri:
        return None
    return uri.strip().rstrip("/")


def get_top_match_uri(match_result):
    if not match_result:
        return None
    matches = match_result.get("matches", [])
    if not matches:
        return None
    top = matches[0]
    if top.get("score", 0) < SCORE_THRESHOLD:
        return None
    return top.get("iri", "")


def get_all_uris(match_result):
    # get all URIs from top-k matches
    if not match_result:
        return []
    matches = match_result.get("matches", [])
    return [m.get("iri") for m in matches if m.get("iri")]


def evaluate():
    rows = load_ground_truth(GROUND_TRUTH_PATH)

    # counters for precision/recall/f-score
    tp = 0
    fp = 0
    fn = 0
    tn = 0

    # counters for top-k accuracy
    top1_correct = 0
    top3_correct = 0
    total_with_gt = 0

    results = []

    for i, row in enumerate(rows):
        environment = row.get("split_environment", "").strip()
        ground_truth_uri = normalize_uri(row.get("matched_environment_envo_uri", ""))

        if not environment:
            continue

        # run ENVO matching
        match_result = match_envo(environment)
        predicted_uri = normalize_uri(get_top_match_uri(match_result))
        all_uris = get_all_uris(match_result)

        # top-k accuracy - only for rows that have a ground truth URI
        in_top1 = False
        in_top3 = False
        if ground_truth_uri:
            total_with_gt += 1
            if all_uris and all_uris[0] == ground_truth_uri:
                top1_correct += 1
                in_top1 = True
            if ground_truth_uri in all_uris:
                top3_correct += 1
                in_top3 = True

        # precision/recall counters
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

        results.append({
            "environment": environment,
            "ground_truth_uri": ground_truth_uri,
            "predicted_uri": predicted_uri,
            "correct": correct,
            "in_top1": in_top1,
            "in_top3": in_top3,
        })

        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(rows)} processed...")

    # precision / recall / f-score
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    # top-k accuracy
    top1_acc = top1_correct / total_with_gt if total_with_gt > 0 else 0
    top3_acc = top3_correct / total_with_gt if total_with_gt > 0 else 0

    print(f"\n--- Evaluation Results ---")
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

    # save results
    output_path = DATA_DIR / "evaluation_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "precision": precision,
            "recall": recall,
            "f_score": f_score,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "top1_accuracy": top1_acc,
            "top3_accuracy": top3_acc,
            "details": results
        }, f, indent=2, ensure_ascii=False)
    print(f"\n[done] Results saved to {output_path}")


if __name__ == "__main__":
    evaluate()