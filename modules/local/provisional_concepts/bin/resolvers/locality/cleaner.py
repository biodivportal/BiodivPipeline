try:
    from clients.llm_client import query_llm
except ImportError:
    import sys
    from pathlib import Path
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.append(str(PROJECT_ROOT))
    from clients.llm_client import query_llm

def split_locality_label(text):
    if not text:
        return {"country": "", "location": "", "environment": "", "rest": ""}

    prompt = f"""You are an expert botanical data parser. Split the location description into country, location, environment, and rest.
Rules:
- country: The country name of origin if explicitly mentioned in the text (even if the specimen was later cultivated elsewhere, e.g. in Berlin), otherwise an empty string.
- location: Geographic placenames of origin, administrative areas, cities, districts, or landmarks. If the plant was collected/originated elsewhere but cultivated in a botanical garden (e.g., 'cult. hort. bot. Berol.', 'Berlin'), the location MUST be the original collection place of origin, NOT the botanical garden or Berlin.
- environment: Terms describing the habitat or environment the plant was found in (e.g., Fichtenwald, auf Muschelkalk, sandige Krautfluren, Krautige Straßenböschung, Bahngelände). Keep this strictly to environment/habitat terms.
- rest: Everything else, including collection dates, collectors, collection numbers, elevations/altitudes, grid references (e.g. TK 8432/3), or botanical garden cultivation notes (e.g., cult. hort. bot. Berol.).
Example 1: 'Germany: Mittelrhein-Gebiet, Namedyer Werth nördl. Andernach, in Hochstaudenbeständen am Leinpfad. 27.08.1988, Leg.: R. Wisskirchen 913.' -> {{"country": "Germany", "location": "Mittelrhein-Gebiet, Namedyer Werth nördl. Andernach, Leinpfad", "environment": "in Hochstaudenbeständen", "rest": "27.08.1988, Leg.: R. Wisskirchen 913."}}
Example 2: 'Germany: Hessen, Limburger Becken, Runkel-Steeden, Bahngelände in Kerkerbach. 08.05.1983, Leg.: H. Kalheber 83-1812. ex herb. / ded. : ex Herbarium Heinz Kalheber.' -> {{"country": "Germany", "location": "Hessen, Limburger Becken, Runkel-Steeden, Kerkerbach", "environment": "Bahngelände", "rest": "08.05.1983, Leg.: H. Kalheber 83-1812. ex herb. / ded. : ex Herbarium Heinz Kalheber."}}
Example 3: 'Origin: Greece, Thessalia. Cultivated in Berlin Botanical Garden. 15.07.1904, Leg.: J. Bornmüller.' -> {{"country": "Greece", "location": "Thessalia", "environment": "", "rest": "Cultivated in Berlin Botanical Garden. 15.07.1904, Leg.: J. Bornmüller."}}
Input to parse: '{text}'"""

    # Could be updated to have the rest split aswell (currently implemented this way to reduce token usage slightly
    schema = {
        "type": "object",
        "properties": {
            "country": {"type": "string"},
            "location": {"type": "string"},
            "environment": {"type": "string"},
            "rest": {"type": "string"},
        },
        "required": ["country", "location", "environment", "rest"],
    }

    return query_llm(
        prompt=prompt,
        system_instruction="You are a data parser. Always return JSON matching the schema.",
        schema=schema,
    )

def clean_locality_text(field_short):
    """
    Helper to extract just the environment descriptor from the locality text.
    Args:
        field_short (str): Locality text to extract descriptor from
    Returns:
        str: Cleaned environment/habitat description
    """
    parsed = split_locality_label(field_short)
    return parsed.get("environment", "").strip()
