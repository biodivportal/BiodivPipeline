#!/usr/bin/env python3
"""Assemble the single quality-annotated, taxonomically resolved dataset.

This satisfies output (i) of Lastenheft Requirement 1: "a quality-annotated and
taxonomically resolved version of the dataset". The individual modules each emit
their own slice (annotated records, taxonomy resolution, quality flags); this
script joins them back into one CSV keyed on the record identifier.

Join strategy
-------------
The record identifier may appear under different column headers across modules
(e.g. ``HerbariumID`` in the annotated export vs. ``record_id`` in the taxonomy
and quality outputs) but the *value* — the herbarium accession — is stable. We
therefore detect each file's id column independently and join on the value.

Pure standard library only, so it runs on the host executor without extra
dependencies (mirrors the other host-run modules).
"""

from __future__ import annotations

import argparse
import csv
import os


SEVERITY_ORDER = {"info": 1, "notice": 1, "warning": 2, "error": 3, "critical": 4}


def _read_rows(path: str | None) -> tuple[list[dict], list[str]]:
    if not path or not os.path.exists(path) or os.path.getsize(path) == 0:
        return [], []
    if os.path.basename(path) == "NO_FILE":
        return [], []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
        except csv.Error:
            delimiter = ","
        reader = csv.DictReader(fh, delimiter=delimiter)
        if reader.fieldnames is None:
            return [], []
        return [row for row in reader], list(reader.fieldnames)


def _detect_id_column(fieldnames: list[str]) -> str | None:
    if not fieldnames:
        return None
    for candidate in ("record_id", "HerbariumID", "id", "ID"):
        if candidate in fieldnames:
            return candidate
    return fieldnames[0]


def _index_by_id(rows: list[dict], id_col: str | None) -> dict:
    index = {}
    if not id_col:
        return index
    for row in rows:
        key = row.get(id_col)
        if key is not None:
            index[key] = row
    return index


def _max_severity(current: str, candidate: str) -> str:
    if not current:
        return candidate
    if SEVERITY_ORDER.get(candidate.lower(), 0) > SEVERITY_ORDER.get(current.lower(), 0):
        return candidate
    return current


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble the unified BiodivPipeline dataset.")
    parser.add_argument("--base", required=True, help="Annotated/standardised records CSV (base table).")
    parser.add_argument("--taxonomy", help="Taxonomy resolution CSV.")
    parser.add_argument("--flagged", help="Quality flags CSV.")
    parser.add_argument("--out", default="final_dataset.csv")
    args = parser.parse_args()

    base_rows, base_fields = _read_rows(args.base)
    if not base_rows:
        # Nothing to assemble — still emit a valid (empty) file so the channel contract holds.
        with open(args.out, "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(base_fields)
        return

    base_id = _detect_id_column(base_fields)

    # --- taxonomy: append columns that are new relative to the base table ---
    tax_rows, tax_fields = _read_rows(args.taxonomy)
    tax_id = _detect_id_column(tax_fields)
    tax_new_cols = [c for c in tax_fields if c != tax_id and c not in base_fields]
    tax_index = _index_by_id(tax_rows, tax_id)

    # --- quality flags ---
    # Two shapes are supported:
    #   legacy: many rows per record keyed by an id column (record_id, issue_type,
    #           severity, ...) -> aggregate into quality_* summary columns.
    #   current: one row per record aligned to the input, with detector columns
    #           (outlier_detected, outlier_severity, ...) and no id column -> append
    #           those columns, joined by id where possible, otherwise by position.
    flag_rows, flag_fields = _read_rows(args.flagged)
    flag_id = _detect_id_column(flag_fields)
    base_ids = {row.get(base_id) for row in base_rows}

    id_join = False
    if flag_id and flag_rows:
        sample_keys = {r.get(flag_id) for r in flag_rows[:25]}
        id_join = len(sample_keys & base_ids) > 0

    legacy_flags = id_join and ("issue_type" in flag_fields or "severity" in flag_fields)

    quality: dict[str, dict] = {}
    flag_index: dict = {}
    if legacy_flags:
        for row in flag_rows:
            key = row.get(flag_id)
            if key is None:
                continue
            agg = quality.setdefault(key, {"count": 0, "severity": "", "issues": []})
            agg["count"] += 1
            agg["severity"] = _max_severity(agg["severity"], (row.get("severity") or "").strip())
            issue = (row.get("issue_type") or "").strip()
            field = (row.get("field") or "").strip()
            label = f"{issue}:{field}" if field else issue
            if label:
                agg["issues"].append(label)
        extra_cols = ["quality_issue_count", "quality_max_severity", "quality_issues"]
    else:
        if id_join:
            flag_index = _index_by_id(flag_rows, flag_id)
            # A genuine id column exists; don't carry it into the output.
            extra_cols = [c for c in flag_fields if c not in base_fields and c not in tax_new_cols and c != flag_id]
        else:
            # No real id column (positional join); keep every flag column, including
            # the leading one that _detect_id_column fell back to.
            extra_cols = [c for c in flag_fields if c not in base_fields and c not in tax_new_cols]

    out_fields = base_fields + tax_new_cols + extra_cols
    positional_ok = (not legacy_flags) and len(flag_rows) == len(base_rows)

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=out_fields, extrasaction="ignore")
        writer.writeheader()
        for idx, row in enumerate(base_rows):
            key = row.get(base_id)

            tax_match = tax_index.get(key, {})
            for col in tax_new_cols:
                row[col] = tax_match.get(col, "")

            if legacy_flags:
                agg = quality.get(key)
                if agg:
                    row["quality_issue_count"] = agg["count"]
                    row["quality_max_severity"] = agg["severity"]
                    row["quality_issues"] = "; ".join(agg["issues"])
                else:
                    row["quality_issue_count"] = 0
                    row["quality_max_severity"] = ""
                    row["quality_issues"] = ""
            else:
                flag_row = flag_index.get(key) if id_join else None
                if flag_row is None and positional_ok:
                    flag_row = flag_rows[idx]
                for col in extra_cols:
                    row[col] = (flag_row or {}).get(col, "")

            writer.writerow(row)


if __name__ == "__main__":
    main()
