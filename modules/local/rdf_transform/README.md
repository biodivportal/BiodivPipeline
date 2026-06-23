# RDF Matching and Transformation Service

A FastAPI microservice that turns tabular biodiversity records (CSV /
TSV / JSON) into RDF using an [RML](https://rml.io/) mapping produced by
the WP7 Schema Editor. The transformation engine is
[Morph-KGC](https://github.com/morph-kgc/morph-kgc) (a maintained,
pure-Python RML engine). The output vocabulary is whatever the mapping
defines — the shipped example targets OBOE 1.2. Part of the BiodivPipeline
WP8 work-package, developed with InfAI and the BGBM.

> **Why RML instead of Karma?** The previous version drove the archived
> Web-Karma JAR over a JVM subprocess. RML is the open, maintained
> standard that does the same job (a declarative "column X → RDF
> property Y" mapping); Morph-KGC consumes it directly into an
> `rdflib.Graph`. No Java, no vendor lock-in — the same RML mapping also
> runs on other engines (SDM-RDFizer, RMLMapper). The RML mapping in
> `examples/` is verified to produce RDF isomorphic to the original
> Karma output.

## Quick start

```bash
docker run --rm -p 8000:8000 --name rdf-transform \
  ghcr.io/biodivportal/rdf-matching-and-transformation-service:latest
```

Swagger UI then at http://127.0.0.1:8000/docs. (Requires the image to be
published and public first — see
[Service image](#service-image--nf-core-module).) If port 8000 is already in
use, map another, e.g. `-p 8001:8000`, and use that port in the URLs below.

To build and run the image locally instead (pure Python, no build args):

```bash
docker build -t rdf-transform .
docker run --rm -p 8000:8000 rdf-transform
```

## `POST /transform`

Multipart form. Required: `dataset` (file), `mapping_schema` (file, an
RML mapping). Optional:

| field           | default  | notes                                          |
| --------------- | -------- | ---------------------------------------------- |
| `source_type`   | `CSV`    | `CSV` / `TSV` / `JSON`                          |
| `delimiter`     | `COMMA`  | `COMMA`, `TAB`, `;` — tabular input only        |
| `output_format` | `turtle` | `turtle`, `ntriples`, `jsonld`                 |
| `mapping_format`| (auto)   | `turtle` or `json-ld`; auto-detected from name |

The mapping bakes its data path into `rml:source`; the service rewrites
that to point at the uploaded dataset, so whatever path the Schema Editor
wrote is irrelevant. Any-delimiter tabular input is normalised to a comma
CSV before materialization. The mapping may be **Turtle or JSON-LD** —
both are just serializations of the same RML graph.

Example against the InfAI sample under `examples/`:

```bash
curl -X POST http://127.0.0.1:8000/transform \
  -F "dataset=@examples/plant_height_vegetative_raw_germany_20.csv" \
  -F "mapping_schema=@examples/plant_height_vegetative_raw-model_oboe.rml.ttl" \
  -F "source_type=CSV" \
  -F "delimiter=TAB" \
  -o out.ttl
```

The same dataset as a JSON array of objects
(`plant_height_vegetative_raw_germany_20.json` — keys match the CSV
column names, so the *same* RML mapping applies). Set `source_type=JSON`;
`delimiter` is irrelevant for JSON. Request `jsonld` output here too:

```bash
curl -X POST http://127.0.0.1:8000/transform \
  -F "dataset=@examples/plant_height_vegetative_raw_germany_20.json" \
  -F "mapping_schema=@examples/plant_height_vegetative_raw-model_oboe.rml.ttl" \
  -F "source_type=JSON" \
  -F "output_format=jsonld" \
  -o out.jsonld
```

Other endpoints: `GET /` (health, also reports loaded ontologies),
`GET /schemas` (lists supported mapping formats), `POST /validate`.

## `POST /validate`

Pre-flight check for an RML mapping. Catches three classes of problem
*before* `/transform` produces RDF that points into the void:

- **L1** — does the file parse as RDF (Turtle or JSON-LD)?
- **L2** — is it actually an RML mapping (declares an `rml:subjectMap`
  and a logical source)? Accepts the modern RML (w3id), legacy RML
  (mmlab) and R2RML (rr) vocabularies.
- **L3** — does every IRI the mapping references in a loaded ontology's
  namespace (OBOE, Darwin Core and ABCD today) actually exist there? Catches
  typos like `oboe-core:Observatoin` and references to renamed/removed
  upstream classes.

```bash
curl -X POST http://127.0.0.1:8000/validate \
  -F "mapping_schema=@examples/plant_height_vegetative_raw-model_oboe.rml.ttl"
# → {"valid": true, "issues": []}
```

Any finding sets `valid: false` and lists the issues with an `[L1]` /
`[L2]` / `[L3]` prefix. Reference ontologies are loaded once at service
start from `$ONTOLOGIES_DIR` (default `/app/ontologies` in the container,
`ontologies/` locally); drop additional `.owl` / `.ttl` files in there to
extend L3 coverage (OBOE, Darwin Core and ABCD ship today; BiodivOntology
follows once a clean RDF artefact is available).

## Engine: Morph-KGC + RML

The transformation runs [Morph-KGC](https://github.com/morph-kgc/morph-kgc)
in-process. It consumes an RML mapping (the open
[KG-Construct](https://kg-construct.github.io/) standard, a superset of
R2RML that also maps CSV/JSON/XML) and returns an `rdflib.Graph`, which
the route serializes to the requested format. Transformations (e.g. the
`UnitName → QUDT IRI` uppercasing in the sample) are expressed with RML's
FNML functions — the sample uses the built-in `concat` + `toUpperCase`,
so no custom code ships in the mapping.

The sample mapping `examples/plant_height_vegetative_raw-model_oboe.rml.ttl`
is the reference for what the Schema Editor must emit; the original Karma
model (`…_oboe.ttl`) is kept alongside for comparison only.

## Service image + nf-core module

`.github/workflows/build-service-image.yml` builds the runtime image
(FastAPI + Morph-KGC + OBOE) and pushes it to GitHub Container Registry.
Trigger from the GitHub UI: **Actions → Build Service Image → Run
workflow**, give it a version like `0.1.0`, and the workflow publishes
both `ghcr.io/biodivportal/rdf-matching-and-transformation-service:v0.1.0`
(immutable) and `…:latest` (floating). Manual-only.

GHCR packages are private by default. On the first publish, go to the
repo's **Packages** sidebar → package settings → *Change visibility* →
*Public*, otherwise the Quick Start `docker run` above and the nf-core
module both need a registry login.

The Nextflow module at [`nextflow/main.nf`](nextflow/main.nf) consumes
the `:latest` image. Each nf-task spins up the FastAPI service on
`localhost:8000` inside its own container, calls `/validate` as a
pre-flight check, then hits `/transform` for the actual work. Same code
path the WP7 Schema Editor and any HTTP consumer goes through, so error
responses look identical no matter who's calling. The pre-flight aborts
the task if the mapping has drifted from OBOE (override with
`task.ext.skip_validate = true`).

## Local development

Morph-KGC requires **Python ≥ 3.10** (the runtime image pins 3.11):

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                                    # ~2 s
uvicorn main:app --reload                 # local server on :8000
```

The end-to-end transformation tests carry a `requires_morph` marker and
self-skip if `morph-kgc` can't be imported (e.g. on Python 3.9).

## Pipeline context

```
Input data ──► WP1 nf-core pipeline ──────────────────► Output (RDF)
                                  ▲   ▲   ▲   ▲   ▲   ▲
                                 WP2 WP3 WP4 WP5 WP6 WP7 WP8 (this repo)
```

WP8 consumes the standardised, quality-checked dataset from WP2–WP6 and
an RML mapping from the WP7 Schema Editor, and emits RDF for downstream
consumers (NFDI knowledge graph).

## Ontologies

Primary: [OBOE 1.2](http://ecoinformatics.org/oboe/oboe.1.2/) — each row
becomes an `ObservationCollection` with `Observation` → `Measurement` →
`MeasuredValue` of an `Entity` (taxon, Catalogue of Life URI) for a
`Characteristic` (trait, TOP Thesaurus) in a `Unit` (QUDT). Secondary
alignment targets per the Lastenheft — Darwin Core RDF, ABCD,
BiodivOntology — are modelled in the WP7 cross-walks and will be
validated by `/validate` once wired up.

## Repo layout

```
.
├── .github/workflows/                      # CI: build-service-image
├── Dockerfile                              # pure-Python runtime
├── main.py                                 # uvicorn entrypoint
├── src/
│   ├── api/                                # routes + pydantic models
│   └── core/morph_runner.py                # Morph-KGC RML materialization
├── examples/                               # InfAI sample + RML mapping + ground truth
├── ontologies/                             # reference ontologies for /validate L3 (OBOE, Darwin Core, ABCD)
├── tests/                                  # pytest
└── nextflow/                               # nf-core module
```

## References

- [RML](https://rml.io/) — RDF Mapping Language (KG-Construct Community Group)
- [Morph-KGC](https://github.com/morph-kgc/morph-kgc) — the RML engine (Apache-2.0)
- [OBOE 1.2](http://ecoinformatics.org/oboe/oboe.1.2/)
- [BiodivPipeline (nf-core)](https://nf-co.re)
- [Web-Karma](https://github.com/usc-isi-i2/Web-Karma) — the prior engine (archived 2025-04-16)

## Contact

InfAI — Naouel Karam (`karam@infai.org`), Jan Fillies (`fillies@infai.org`).
