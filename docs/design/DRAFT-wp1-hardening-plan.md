# RFC: WP1 Pipeline Hardening

**Status:** Draft — request for comments

Follow-up work for the BiodivPipeline (WP1). WP2–WP8 internals belong to other teams;
everything proposed here is WP1-owned. This is a proposal, not a fixed plan — feedback,
pushback, and volunteers on any item are welcome.

## Motivation

The pipeline now runs end-to-end and produces two of the three outputs mandated by
Lastenheft Requirement 1. Getting from "runs on our machines" to "meets the spec and
survives other teams' changes" still needs work in three areas:

- **Correctness we can trust.** The report/dataset logic already broke once when WP3/WP4/WP6
  changed their output formats, and a caching quirk means edits to our scripts don't always
  re-run. We want these to fail loudly, not silently.
- **Spec coverage.** Requirement 1 asks for CSV *and* DwC-A input and "nf-core best
  practices"; we currently handle only CSV and have never run the linter.
- **Readiness for other teams.** When WP7 (RDF) and WP8 (schema editor) land, integrating
  them should be a config change, not a scramble. Clear interface docs and a clean
  `mapping_schema` seam get us there.

## Status

- Outputs **(i)** `final_dataset.csv` and **(iii)** `pipeline_summary.{json,md}` — implemented on `wp1-enhancement-reports`.
- Output **(ii)** RDF — blocked on WP7 (stub); WP1 owns only the wiring.

## Proposed tasks

Each task lists *what* and *why*. Effort is a rough guess to help people self-select.

### A — Make the `bin/` scripts hashable (effort: medium)

**What:** move `collect_reports.py` and `assemble_dataset.py` out of the module dirs into
the pipeline-level `bin/` (shebang, `chmod +x`, call by bare name), and update both module
`main.nf` files.

**Why:** the scripts are currently called via `${moduleDir}/bin/...`, which Nextflow does
*not* include in a task's hash. Editing a script therefore doesn't invalidate the `-resume`
cache — we had to manually delete work dirs to force a re-run. Scripts in the top-level
`bin/` are staged and hashed, so caching behaves correctly.

### F — Guard the outlier (WP4) join (effort: easy — depends on A)

**What:** in `assemble_dataset`, when the flagged file's row count doesn't match the base,
warn and omit the quality columns rather than guessing, and record `quality_join: "skipped"`
in the summary. Use an id-based join whenever an id column is present.

**Why:** WP4 currently emits no record id, so we align quality flags by row position. That is
only correct while every module preserves input order — if one ever filters or reorders rows,
the quality columns would attach to the wrong records with no warning. The quality fields are
enrichment, so omitting them is safer than a hard failure or a silent mismatch.

### B — pytest coverage for the two scripts (effort: medium — depends on A, F)

**What:** add `pytest` tests under `tests/python/` with small fixtures covering both the
current and legacy schemas (WP6 list vs dict, WP3 `;` vs `,`, WP4 `outlier_*` vs
`issue_type`). Run manually.

**Why:** the drift-prone parsing and join logic has zero automated coverage today, and it is
exactly where the last breakage happened. Unit tests on the scripts catch schema regressions
in under a second without needing containers or secrets.

### C — Minimal DwC-A input (effort: hard)

**What:** a `DWCA_EXTRACT` front module that detects a Darwin Core Archive (`.zip` with
`meta.xml`), extracts the occurrence *core* to CSV using the delimiter/columns from
`meta.xml`, and feeds `COLUMN_STANDARDISE`. Extensions and multi-core archives out of scope
for now.

**Why:** Requirement 1 explicitly says the pipeline must accept "CSV / DwC-A"; today it only
accepts CSV, so this closes a literal spec gap. Minimal occurrence-core support covers typical
BGBM exports without opening the full DwC-A parsing rabbit hole.

### D — nf-core lint pass (effort: easy→medium)

**What:** run `nf-core lint`, fix the easy findings, and list the rest with notes.

**Why:** Requirement 1 asks for "nf-core community best practices," and a clean lint run is the
most direct evidence of that. It also surfaces template/config drift early rather than at
hand-in.

### E1 — Containerise our two modules (effort: medium — depends on A)

**What:** add a slim `python` Dockerfile and `container` directive for `assemble_dataset` and
`collect_reports`.

**Why:** these two run on the host today, so reproducibility depends on the host having
`python3`. Containers make them reproducible anywhere and bring them in line with the other
modules. Because the scripts are pure stdlib, the image is essentially `python:slim`.

### G — Interface-contract doc (effort: easy)

**What:** one concise `docs/module-interfaces.md` describing each output we consume —
filename, delimiter, key fields, and the record-id column (or "positional"). Replace the vague
"each module's interface spec" reference in `output.md`.

**Why:** the WP3/4/6 schema changes that broke us were undocumented. A single consumer-side
contract catches drift in one place and doubles as the thing we hand other teams to say "please
keep this stable / add a record id."

### H — README / usage refresh (effort: easy)

**What:** note that the docker profile now works, document `-profile test,docker,emulate_amd64`
for Apple Silicon, and drop the "does not work yet" caveat.

**Why:** the README currently tells people the docker path is broken, which is no longer true —
a new contributor can't reliably run the pipeline from the docs as written.

### I — `mapping_schema` validation (effort: easy)

**What:** warn and continue when the empty placeholder schema is used; add
`--require_mapping_schema` (default `false`); record `rdf.mapping_schema: "placeholder"` in the
summary.

**Why:** the RDF step silently produces empty output when no real schema is supplied, which is
easy to miss. A warning makes it visible now, and the flag lets us enforce a real schema once
WP7/WP8 deliver — without blocking the pipeline on their work in the meantime.

## Dependencies & sequencing

`A → F → B` touch the same two scripts, so they are best done together on one branch, in that
order. `E1` builds on A's final script location. `C`, `D`, `G`, `H`, `I` are independent and
can proceed in parallel. Suggested branching: one short-lived branch per task off `dev`, small
PRs, tests run manually (no CI proposed yet).

## Cross-team coordination

- Ask **WP4** to emit a `record_id` in `flagged_records.csv`; this would make the quality join
  robust and retire the positional fallback in F.
- The demo images live under `ghcr.io/mitchell7970/…`; moving them to the org registry needs
  registry access.

## Open questions (comments welcome)

- Host-run scripts (A) vs. full containerisation (E1) — is deferring E1 acceptable, or should we
  containerise in one pass?
- Is minimal occurrence-core DwC-A enough for the BGBM data, or do we need extensions?
- Do we want CI eventually, and if so what should it run (pytest is cheap; full `nf-test` needs
  secrets + containers)?
- Should `--require_mapping_schema` default to fail-fast once WP7 is real?
