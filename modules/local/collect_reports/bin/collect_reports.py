#!/usr/bin/env python3
"""Aggregate the per-step outputs of the BiodivPipeline into a single quality report.

This satisfies output (iii) of Lastenheft Requirement 1: "quality reports for each
processing step". It reads whatever each upstream module emitted and produces:

  * pipeline_summary.json  — machine-readable per-step statistics
  * pipeline_summary.md    — human-readable overview

The parser is intentionally defensive: every module output is owned by a different
work-package team and its schema may evolve, so missing files, empty files and
unexpected columns must never crash the run.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _is_placeholder(path: str | None) -> bool:
    """True when a file is absent, empty, the NO_FILE stub, or empty JSON ({})."""
    if not path or not os.path.exists(path):
        return True
    if os.path.basename(path) == "NO_FILE":
        return True
    if os.path.getsize(path) == 0:
        return True
    return False


def _load_json(path: str | None):
    if _is_placeholder(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None
    if data in ({}, []):
        return None
    return data


def _read_rows(path: str | None) -> list[dict]:
    if _is_placeholder(path):
        return []
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            sample = fh.read(4096)
            fh.seek(0)
            try:
                delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
            except csv.Error:
                delimiter = ","
            reader = csv.DictReader(fh, delimiter=delimiter)
            if reader.fieldnames is None:
                return []
            return [row for row in reader]
    except OSError:
        return []


def _detect_id_column(fieldnames: list[str] | None) -> str | None:
    if not fieldnames:
        return None
    for candidate in ("record_id", "HerbariumID", "id", "ID"):
        if candidate in fieldnames:
            return candidate
    return fieldnames[0]


# ---------------------------------------------------------------------------
# per-step summarisers
# ---------------------------------------------------------------------------

def summarise_columns(path: str | None) -> dict:
    mapping = _load_json(path)
    # Legacy WP6 schema: flat { original_header: standard_name }.
    if isinstance(mapping, dict) and mapping:
        return {"status": "ok", "columns_mapped": len(mapping), "mapping": mapping}
    # Current WP6 schema: [ { header, predicted_header, confidence, review_flag } ].
    if isinstance(mapping, list) and mapping:
        confidences = []
        review = 0
        for item in mapping:
            if not isinstance(item, dict):
                continue
            try:
                confidences.append(float(item.get("confidence")))
            except (TypeError, ValueError):
                pass
            if item.get("review_flag"):
                review += 1
        out = {"status": "ok", "columns_mapped": len(mapping), "flagged_for_review": review}
        if confidences:
            out["mean_confidence"] = round(sum(confidences) / len(confidences), 4)
        return out
    return {"status": "no_data", "columns_mapped": 0}


def summarise_annotation(path: str | None) -> dict:
    rows = _read_rows(path)
    occurrences = 0
    for row in rows:
        try:
            occurrences += int(row.get("count", 0) or 0)
        except (TypeError, ValueError):
            occurrences += 0
    return {
        "status": "ok" if rows else "no_data",
        "unresolved_terms": len(rows),
        "unresolved_occurrences": occurrences,
    }


def summarise_taxonomy(path: str | None) -> dict:
    rows = _read_rows(path)
    if not rows:
        return {"status": "no_data", "records": 0, "resolved": 0}
    confidences = []
    resolved = 0
    for row in rows:
        # Current WP3 fields: taxon_status / taxon_identifier / taxon_confidence.
        # Legacy fields: status / gbif_key / confidence.
        status = (row.get("taxon_status") or row.get("status") or "").strip().lower()
        ident = (row.get("taxon_identifier") or row.get("gbif_key") or "").strip()
        if ident or status in ("resolved", "matched", "success", "accepted"):
            resolved += 1
        for key in ("taxon_confidence", "confidence"):
            val = row.get(key)
            if val not in (None, ""):
                try:
                    confidences.append(float(val))
                    break
                except (TypeError, ValueError):
                    pass
    out = {"status": "ok", "records": len(rows), "resolved": resolved}
    if confidences:
        out["mean_confidence"] = round(sum(confidences) / len(confidences), 4)
    return out


def summarise_quality(path: str | None) -> dict:
    rows = _read_rows(path)
    if not rows:
        return {"status": "no_data", "records": 0, "flagged": 0}
    fields = list(rows[0].keys())

    # Current WP4 schema: one row per record with an outlier_detected boolean.
    if "outlier_detected" in fields:
        flagged = 0
        by_severity: dict[str, int] = {}
        by_detector: dict[str, int] = {}
        for row in rows:
            detected = str(row.get("outlier_detected", "")).strip().lower() in ("true", "1", "yes")
            if not detected:
                continue
            flagged += 1
            sev = (row.get("outlier_severity") or "unknown").strip() or "unknown"
            by_severity[sev] = by_severity.get(sev, 0) + 1
            det = (row.get("outlier_primary_detector") or "unknown").strip() or "unknown"
            by_detector[det] = by_detector.get(det, 0) + 1
        return {
            "status": "ok",
            "records": len(rows),
            "flagged": flagged,
            "by_severity": dict(sorted(by_severity.items())),
            "by_detector": dict(sorted(by_detector.items())),
        }

    # Legacy schema: one row per flag (record_id, issue_type, severity, ...).
    by_severity = {}
    by_issue: dict[str, int] = {}
    flagged_ids = set()
    id_col = _detect_id_column(fields)
    for row in rows:
        sev = (row.get("severity") or "unknown").strip() or "unknown"
        issue = (row.get("issue_type") or "unknown").strip() or "unknown"
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_issue[issue] = by_issue.get(issue, 0) + 1
        if id_col:
            flagged_ids.add(row.get(id_col))
    return {
        "status": "ok",
        "total_flags": len(rows),
        "records_flagged": len(flagged_ids),
        "by_severity": dict(sorted(by_severity.items())),
        "by_issue_type": dict(sorted(by_issue.items())),
    }


def summarise_concepts(path: str | None) -> dict:
    if _is_placeholder(path):
        return {"status": "skipped", "registered": 0}
    data = _load_json(path)
    if data is None:
        return {"status": "skipped", "registered": 0}
    concepts = data.get("provisional_concepts", []) if isinstance(data, dict) else []
    by_category: dict[str, int] = {}
    for concept in concepts:
        if not isinstance(concept, dict):
            continue
        key = concept.get("status") or concept.get("suggested_category") or "unknown"
        by_category[key] = by_category.get(key, 0) + 1
    out = {"status": "ok", "registered": len(concepts)}
    if by_category:
        out["by_category"] = dict(sorted(by_category.items()))
    return out


def summarise_rdf(path: str | None) -> dict:
    if _is_placeholder(path):
        return {"status": "skipped"}
    data = _load_json(path)
    if not isinstance(data, dict):
        return {"status": "no_data"}
    # Current WP7 service emits a /validate response: {valid: bool, issues: [...]}.
    if "valid" in data:
        issues = data.get("issues") or []
        return {
            "status": "validated" if data.get("valid") else "invalid",
            "valid": bool(data.get("valid")),
            "issues": len(issues) if isinstance(issues, list) else issues,
        }
    # Legacy stub report: {records_transformed, triples_generated, ...}.
    keep = ("records_transformed", "triples_generated", "formats", "status", "mapping_schema_used")
    out = {k: data[k] for k in keep if k in data}
    out.setdefault("status", "ok")
    return out


# ---------------------------------------------------------------------------
# markdown rendering
# ---------------------------------------------------------------------------

def render_markdown(summary: dict) -> str:
    steps = summary["steps"]
    lines = [
        "# BiodivPipeline — Quality Report",
        "",
        f"_Generated: {summary['generated_at']}_",
        "",
        "Per-step quality reports (Lastenheft Requirement 1, output iii).",
        "",
        "| Step | Key metrics |",
        "| ---- | ----------- |",
    ]

    col = steps["column_standardisation"]
    col_metric = f"{col.get('columns_mapped', 0)} columns mapped to ABCD terms"
    if "flagged_for_review" in col:
        col_metric += f" ({col['flagged_for_review']} flagged for review)"
    lines.append(f"| WP6 Column standardisation | {col_metric} |")

    ann = steps["annotation"]
    lines.append(
        f"| WP2 Annotation | {ann.get('unresolved_terms', 0)} unresolved terms "
        f"({ann.get('unresolved_occurrences', 0)} occurrences) |"
    )

    tax = steps["taxonomy"]
    tax_conf = f", mean confidence {tax['mean_confidence']}" if "mean_confidence" in tax else ""
    lines.append(
        f"| WP3 Taxonomy | {tax.get('resolved', 0)}/{tax.get('records', 0)} records resolved{tax_conf} |"
    )

    qual = steps["quality"]
    sev = ", ".join(f"{k}: {v}" for k, v in qual.get("by_severity", {}).items()) or "none"
    if "flagged" in qual:
        # Current per-record schema.
        lines.append(
            f"| WP4 Outlier / quality | {qual.get('flagged', 0)}/{qual.get('records', 0)} records "
            f"flagged (severity — {sev}) |"
        )
    else:
        # Legacy per-flag schema.
        lines.append(
            f"| WP4 Outlier / quality | {qual.get('total_flags', 0)} flags on "
            f"{qual.get('records_flagged', 0)} records (severity — {sev}) |"
        )

    con = steps["provisional_concepts"]
    if con.get("status") == "skipped":
        lines.append("| WP5 Provisional concepts | skipped |")
    else:
        lines.append(f"| WP5 Provisional concepts | {con.get('registered', 0)} provisional concepts registered |")

    rdf = steps["rdf"]
    if rdf.get("status") == "skipped":
        rdf_metric = "skipped"
    elif "valid" in rdf:
        rdf_metric = f"model {'valid' if rdf['valid'] else 'INVALID'} ({rdf.get('issues', 0)} issues)"
    else:
        rdf_metric = (
            f"{rdf.get('triples_generated', 0)} triples from "
            f"{rdf.get('records_transformed', 0)} records ({rdf.get('status', 'n/a')})"
        )
    lines.append(f"| WP7 RDF transform | {rdf_metric} |")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate BiodivPipeline per-step reports.")
    parser.add_argument("--column-mapping")
    parser.add_argument("--annotation-unresolved")
    parser.add_argument("--taxonomy")
    parser.add_argument("--flagged")
    parser.add_argument("--concepts")
    parser.add_argument("--rdf-report")
    parser.add_argument("--out-json", default="pipeline_summary.json")
    parser.add_argument("--out-md", default="pipeline_summary.md")
    args = parser.parse_args()

    summary = {
        "pipeline": "nf-core/biodivpipeline",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "steps": {
            "column_standardisation": summarise_columns(args.column_mapping),
            "annotation": summarise_annotation(args.annotation_unresolved),
            "taxonomy": summarise_taxonomy(args.taxonomy),
            "quality": summarise_quality(args.flagged),
            "provisional_concepts": summarise_concepts(args.concepts),
            "rdf": summarise_rdf(args.rdf_report),
        },
    }

    with open(args.out_json, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    with open(args.out_md, "w", encoding="utf-8") as fh:
        fh.write(render_markdown(summary))


if __name__ == "__main__":
    main()
