"""Unit tests for `morph_runner` — the pieces that don't need the Morph-KGC
engine itself (dataset normalisation, mapping source rewriting, error paths)
run everywhere; the end-to-end materialization is covered in
test_transformation.py behind the `requires_morph` marker."""
from __future__ import annotations

import pytest

from tests.conftest import requires_morph


@requires_morph
def test_rewrite_mapping_sources_points_at_dataset(tmp_path):
    from src.core.morph_runner import _rewrite_mapping_sources

    mapping = b"""
    @prefix rml: <http://w3id.org/rml/> .
    <#TM> a rml:TriplesMap ;
        rml:logicalSource [ rml:source "whatever-the-ui-wrote.csv" ;
                            rml:referenceFormulation rml:CSV ] ;
        rml:subjectMap [ rml:template "http://ex/{id}" ] .
    """
    dataset = tmp_path / "dataset.csv"
    out = _rewrite_mapping_sources(mapping, "turtle", dataset, tmp_path)

    text = out.read_text()
    assert str(dataset) in text
    assert "whatever-the-ui-wrote.csv" not in text


@requires_morph
def test_rewrite_rejects_mapping_without_source(tmp_path):
    from src.core.morph_runner import MorphError, _rewrite_mapping_sources

    mapping = b"@prefix ex: <http://example.org/> .\nex:s ex:p ex:o ."
    with pytest.raises(MorphError, match="no rml:source"):
        _rewrite_mapping_sources(mapping, "turtle", tmp_path / "d.csv", tmp_path)


@requires_morph
def test_normalize_dataset_writes_json_verbatim(tmp_path):
    from src.core.morph_runner import _normalize_dataset

    raw = b'[{"a": "1"}]'
    path = _normalize_dataset(raw, "JSON", "COMMA", tmp_path)
    assert path.suffix == ".json"
    assert path.read_bytes() == raw


@requires_morph
def test_normalize_dataset_converts_tab_to_comma_csv(tmp_path):
    from src.core.morph_runner import _normalize_dataset

    raw = b"a\tb\n1\t2\n"
    path = _normalize_dataset(raw, "CSV", "TAB", tmp_path)
    assert path.suffix == ".csv"
    assert path.read_text().splitlines()[0] == "a,b"
