# Reference Ontologies

Runtime reference data for the service's `/validate` L3 check (ontology-term
alignment): the loader indexes every `.owl`/`.ttl`/`.rdf`/`.nt` file here at
startup and flags any IRI a mapping references in one of these namespaces that
isn't declared. Mounted into the image at `/app/ontologies` (override the
location with `ONTOLOGIES_DIR`). Drop additional vocabularies here to extend
L3 coverage — no code change needed.

- `oboe.owl` — OBOE 1.2 core ontology, from https://github.com/NCEAS/oboe.
- `darwin-core.ttl` — Darwin Core terms (classes + properties), generated from
  the authoritative TDWG term list
  `https://raw.githubusercontent.com/tdwg/rs.tdwg.org/master/terms/terms.csv`
  (namespace `http://rs.tdwg.org/dwc/terms/`). Regenerate by reading the CSV
  and emitting one `rdf:type` triple per term from its `rdf_type` column.
- `abcd_concepts.owl` — ABCD 3.0 concept ontology, the upstream TDWG OWL file
  `https://raw.githubusercontent.com/tdwg/abcd/master/ontology/abcd_concepts.owl`
  (namespace `http://rs.tdwg.org/abcd/terms/`). A few upstream instance IRIs
  contain spaces; rdflib warns on serialization but parsing/indexing is
  unaffected (we only read it).

Planned next (per the Lastenheft): BiodivOntology, once it is clear which
artefact is meant (e.g. via InfAI) and a clean RDF file is available.
