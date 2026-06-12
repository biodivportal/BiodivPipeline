"""In-process RML materialization via Morph-KGC (replaces the Karma JAR).

Karma was an archived Java tool driven over a subprocess; Morph-KGC is a
maintained pure-Python engine that consumes the open RML standard and returns
an `rdflib.Graph` directly. The mapping the UI/Schema-Editor produces is RML
(Turtle or JSON-LD); the dataset is CSV/TSV/JSON.

Two things this wrapper smooths over so callers don't have to:

* **Source path.** An RML mapping bakes the data path into `rml:source`.
  Whatever the UI wrote there is irrelevant to us — we rewrite every
  `rml:source` to point at the dataset we actually received.
* **Mapping serialization + delimiter.** We round-trip the mapping through
  rdflib, so a JSON-LD mapping is accepted as readily as Turtle, and we
  normalise any-delimiter tabular input to a comma CSV that Morph-KGC reads
  unambiguously (it infers CSV vs JSON from the source file extension).
"""
from __future__ import annotations

import io
import tempfile
from dataclasses import dataclass
from pathlib import Path

import morph_kgc
import pandas as pd
from rdflib import Graph, Literal, URIRef

# `rml:source` in both the modern (w3id) and legacy (mmlab) RML vocabularies.
# Morph-KGC normalises legacy → modern internally, but we rewrite the mapping
# *before* handing it over, so we must catch both spellings ourselves.
_RML_SOURCE_PREDICATES = (
    URIRef("http://w3id.org/rml/source"),
    URIRef("http://semweb.mmlab.be/ns/rml#source"),
)

# Karma-style delimiter tokens (kept for API compatibility) → pandas `sep`.
_DELIMITERS = {
    "COMMA": ",", ",": ",",
    "TAB": "\t", "\t": "\t",
    "SEMICOLON": ";", ";": ";",
    "PIPE": "|", "|": "|",
}


class MorphError(RuntimeError):
    """Raised when Morph-KGC fails to parse the mapping or materialize RDF."""


@dataclass(frozen=True)
class MorphResult:
    graph: Graph
    triples: int


def _normalize_dataset(dataset_bytes: bytes, source_type: str, delimiter: str,
                       tmp_dir: Path) -> Path:
    """Write the dataset into `tmp_dir` in a form Morph-KGC reads unambiguously.

    JSON is written verbatim as `.json`. Any tabular input is parsed with the
    caller's delimiter and re-emitted as a comma `.csv`, so Morph-KGC's
    extension-based format inference (`.csv` ⇒ comma) is always correct.
    """
    if (source_type or "").upper() == "JSON":
        path = tmp_dir / "dataset.json"
        path.write_bytes(dataset_bytes)
        return path

    sep = _DELIMITERS.get((delimiter or "COMMA").upper(), ",")
    try:
        df = pd.read_csv(io.BytesIO(dataset_bytes), sep=sep, dtype=str,
                         keep_default_na=False)
    except Exception as exc:  # pandas raises a zoo of parse errors
        raise MorphError(f"Could not parse tabular dataset: {exc}") from exc
    path = tmp_dir / "dataset.csv"
    df.to_csv(path, index=False)
    return path


def _rewrite_mapping_sources(mapping_bytes: bytes, mapping_format: str,
                             dataset_path: Path, tmp_dir: Path) -> Path:
    """Parse the RML mapping (Turtle or JSON-LD), point every `rml:source` at
    `dataset_path`, and write it back as Turtle for Morph-KGC."""
    graph = Graph()
    try:
        graph.parse(data=mapping_bytes, format=mapping_format)
    except Exception as exc:
        raise MorphError(
            f"Could not parse mapping as {mapping_format}: {exc}"
        ) from exc

    rewrote = False
    for predicate in _RML_SOURCE_PREDICATES:
        for subject, _ in list(graph.subject_objects(predicate)):
            graph.set((subject, predicate, Literal(str(dataset_path))))
            rewrote = True
    if not rewrote:
        raise MorphError(
            "Mapping declares no rml:source — is this a valid RML mapping?"
        )

    path = tmp_dir / "mapping.rml.ttl"
    path.write_text(graph.serialize(format="turtle"))
    return path


def run_morph(
    *,
    dataset_bytes: bytes,
    mapping_bytes: bytes,
    source_type: str = "CSV",
    delimiter: str = "COMMA",
    mapping_format: str = "turtle",
) -> MorphResult:
    """Materialize RDF from a dataset + RML mapping with Morph-KGC.

    Args:
        dataset_bytes: the raw CSV/TSV/JSON dataset.
        mapping_bytes: the RML mapping, serialized as `mapping_format`.
        source_type: ``"JSON"`` or a tabular type (``"CSV"``/``"TSV"``/…).
        delimiter: Karma-style token (``COMMA``/``TAB``/``;``) for tabular input.
        mapping_format: ``"turtle"`` or ``"json-ld"`` — rdflib parse format.

    Returns:
        MorphResult with the materialized `rdflib.Graph` and its triple count.

    Raises:
        MorphError: the dataset or mapping could not be parsed, or Morph-KGC
            produced no graph.
    """
    with tempfile.TemporaryDirectory(prefix="morph_") as tmp:
        tmp_dir = Path(tmp)
        dataset_path = _normalize_dataset(
            dataset_bytes, source_type, delimiter, tmp_dir
        )
        mapping_path = _rewrite_mapping_sources(
            mapping_bytes, mapping_format, dataset_path, tmp_dir
        )

        config = (
            "[CONFIGURATION]\n"
            "na_values=\n"
            "[DataSource1]\n"
            f"mappings={mapping_path}\n"
        )
        try:
            graph = morph_kgc.materialize(config)
        except Exception as exc:  # Morph-KGC surfaces parse/materialize errors
            raise MorphError(f"Morph-KGC materialization failed: {exc}") from exc

    return MorphResult(graph=graph, triples=len(graph))
