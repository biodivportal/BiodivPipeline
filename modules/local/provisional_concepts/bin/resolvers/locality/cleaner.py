try:
    from clients.llm_client import query_llm, LLM_BATCH_SIZE
except ImportError:
    import sys
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.append(str(PROJECT_ROOT))
    from clients.llm_client import query_llm, LLM_BATCH_SIZE


def split_locality_label(text_or_texts):
    import os

    is_single = isinstance(text_or_texts, str) or text_or_texts is None
    texts = [text_or_texts] if is_single else text_or_texts

    if not texts:
        return []

    non_empty_indices = []
    non_empty_texts = []
    results = [None] * len(texts)

    for idx, text in enumerate(texts):
        if not text:
            results[idx] = {
                "country": "",
                "location": "",
                "environment": "",
                "rest": "",
            }
        else:
            non_empty_indices.append(idx)
            non_empty_texts.append(text)

    if not non_empty_texts:
        return results[0] if is_single else results

    for i in range(0, len(non_empty_texts), LLM_BATCH_SIZE):
        chunk_texts = non_empty_texts[i : i + LLM_BATCH_SIZE]
        chunk_indices = non_empty_indices[i : i + LLM_BATCH_SIZE]

        prompt = """You are an expert botanical data parser. Split the location description into country, location, environment, and rest.
Rules:
- country: The country name of origin if explicitly mentioned in the text (even if the specimen was later cultivated elsewhere, e.g. in Berlin), otherwise an empty string.
- location: Geographic placenames of origin, administrative areas, cities, districts, or landmarks. If the plant was collected/originated elsewhere but cultivated in a botanical garden (e.g., 'cult. hort. bot. Berol.', 'Berlin'), the location MUST be the original collection place of origin, NOT the botanical garden or Berlin.
- environment: Terms describing the habitat or environment the plant was found in (e.g., Fichtenwald, auf Muschelkalk, sandige Krautfluren, Krautige Straßenböschung, Bahngelände). Keep this strictly to environment/habitat terms.
- rest: Everything else, including collection dates, collectors, collection numbers, elevations/altitudes, grid references (e.g. TK 8432/3), or botanical garden cultivation notes (e.g., cult. hort. bot. Berol.).
Example 1: 'Germany: Mittelrhein-Gebiet, Namedyer Werth nördl. Andernach, in Hochstaudenbeständen am Leinpfad. 27.08.1988, Leg.: R. Wisskirchen 913.' -> {"country": "Germany", "location": "Mittelrhein-Gebiet, Namedyer Werth nördl. Andernach, Leinpfad", "environment": "in Hochstaudenbeständen", "rest": "27.08.1988, Leg.: R. Wisskirchen 913."}
Example 2: 'Germany: Hessen, Limburger Becken, Runkel-Steeden, Bahngelände in Kerkerbach. 08.05.1983, Leg.: H. Kalheber 83-1812. ex herb. / ded. : ex Herbarium Heinz Kalheber.' -> {"country": "Germany", "location": "Hessen, Limburger Becken, Runkel-Steeden, Kerkerbach", "environment": "Bahngelände", "rest": "08.05.1983, Leg.: H. Kalheber 83-1812. ex herb. / ded. : ex Herbarium Heinz Kalheber."}
Example 3: 'Origin: Greece, Thessalia. Cultivated in Berlin Botanical Garden. 15.07.1904, Leg.: J. Bornmüller.' -> {"country": "Greece", "location": "Thessalia", "environment": "", "rest": "Cultivated in Berlin Botanical Garden. 15.07.1904, Leg.: J. Bornmüller."}
"""
        if is_single:
            prompt += f"Input to parse: '{chunk_texts[0]}'"
        else:
            prompt += '\nYou must return a JSON object with a single key "results" which maps to a list of parsed objects. Each parsed object must correspond to the input items in the exact same order and must match the required schema.\n\nInput to parse:\n'
            for idx, text in enumerate(chunk_texts):
                prompt += f"Item {idx}: {text}\n"

        schema = (
            {
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "country": {"type": "string"},
                                "location": {"type": "string"},
                                "environment": {"type": "string"},
                                "rest": {"type": "string"},
                            },
                            "required": ["country", "location", "environment", "rest"],
                        },
                    }
                },
                "required": ["results"],
            }
            if not is_single
            else {
                "type": "object",
                "properties": {
                    "country": {"type": "string"},
                    "location": {"type": "string"},
                    "environment": {"type": "string"},
                    "rest": {"type": "string"},
                },
                "required": ["country", "location", "environment", "rest"],
            }
        )

        try:
            response = query_llm(
                prompt=prompt,
                system_instruction="You are a data parser. Always return JSON matching the schema.",
                schema=schema,
            )
            if is_single:
                chunk_results = [response]
            else:
                chunk_results = response.get("results", [])
                if len(chunk_results) != len(chunk_texts):
                    raise ValueError(
                        f"Expected {len(chunk_texts)} results, got {len(chunk_results)}"
                    )
        except Exception as e:
            print(
                f"[Warning] Batch query failed: {e}. Falling back to individual queries."
            )
            chunk_results = [split_locality_label(t) for t in chunk_texts]

        for idx, res in zip(chunk_indices, chunk_results):
            results[idx] = res

    return results[0] if is_single else results


def clean_locality_text(field_short):
    parsed = split_locality_label(field_short)
    return parsed.get("environment", "").strip()
