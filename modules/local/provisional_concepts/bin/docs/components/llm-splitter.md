# LLM Splitter

The LLM splitter parses raw German locality strings into structured fields, extracting habitat descriptions from compound place names and cleaning the input text.

## Role in the pipeline

This is the first stage in locality resolution. It converts raw locality fields into structured outputs containing country, location, environment, English translated environment, and remaining text.

The translated environment string feeds directly into the ENVO matcher. If no environment description is found in the text, the record is flagged as place-only and discarded from further habitat matching.

## How it works

Each non-empty locality string is processed through the LLM batch client to maintain row order. The system prompt enforces strict botanical parsing rules with a structured JSON output schema.

| Field | Description |
|---|---|
| `country` | Country of origin when explicitly named. It excludes cultivation locations such as botanical gardens. |
| `location` | Geographic place names representing origin. |
| `environment` | German habitat terms. German place names often bury habitat words inside compound terms (such as Teufelsmoor or Kühnauer Heide); the splitter extracts the habitat stem while keeping the full place name in location. |
| `environment_EN` | Faithful English translation of the environment term, including translated Latin phrases. |
| `rest` | Auxiliary text such as dates, collector names, catalog numbers, elevation, or cultivation notes. |

The prompt includes common German habitat stems to guide extraction, including moor, heide, wald, wiese, aue, graben, tal, niederung, hang, see, teich, wegrand, and bahngelände.

Examples of parsing results:
- Input `Teufelsmoor`: environment `Moor`, translated environment `bog`
- Input `Kühnauer Heide, NW-Teil`: environment `Heide`, translated environment `heath`
- Input `Edelmannswald, Wegrand`: environment `Wald, Wegrand`, translated environment `forest, roadside`

## Development and evaluation

A significant effort was made to handle this stage deterministically without an LLM. Rule-based parsers, named entity recognition, spaCy pipelines, GLiNER, and specialized German embedding models like SauerkrautLM were evaluated.

None of the non-LLM approaches achieved acceptable accuracy. Botanical locality text is frequently noisy, ungrammatical, heavily abbreviated, and mixed with Latin or collector shorthand, offering too little grammatical structure for standard NLP tools.

An LLM with a constrained JSON schema proved to be the only reliable solution, accepting the trade-offs of latency and token cost.

Translation was originally implemented as an additional Google Translate step. Integrating translation directly into the LLM prompt produced better results for German botanical compounds, Latin terms, and foreign phrases at minimal incremental cost.

## Configuration and inputs

The system prompt and output schema are defined in `resolvers/locality/cleaner.py`. Model configuration and batch settings are managed through environment variables such as `WP5_OPENAI_API_KEY` and related settings.

## Related documentation

- [ENVO matcher](envo-matcher.md): Consumes the translated environment phrase.
- [GeoNames resolver](geonames-resolver.md): Consumes extracted location place names.
- [Decisions and lessons](../research/decisions.md): Further discussion on deterministic parsing attempts.
