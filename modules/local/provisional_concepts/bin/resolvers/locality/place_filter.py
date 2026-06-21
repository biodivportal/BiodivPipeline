
# def filter_placenames(field):
#     """ Uses the geonames client to clean the string
#     Args:
#         field (str): the full unresolved locality string
#     Return:
#         field_short (str): the string without the place names
#         dict locations: the URIs and names of the places found (why not just return it all
#     """
#     field_short = ""
#     locations = dict()
#     return (field_short, locations)

from clients.geonames_client import search, get_country_code
import re

# only accept real geographic features, not hotels/farms etc
GEOGRAPHIC_CLASSES = {"A", "P", "T", "L"}


def normalize(text):
    # convert umlauts for comparison
    return text.lower().replace("ö", "oe").replace("ü", "ue").replace("ä", "ae").replace("ß", "ss")

def is_valid_match(query, raw):
    query_norm = normalize(query)
    name_norm = normalize(raw.get("name", ""))
    toponym_norm = normalize(raw.get("toponymName", ""))
    alt_names_raw = raw.get("alternateNames", [])
    if isinstance(alt_names_raw, list):
        alt_names = normalize(" ".join([a.get("name", "") for a in alt_names_raw]))
    else:
        alt_names = normalize(str(alt_names_raw))
    
    # check full query
    if query_norm in name_norm or query_norm in toponym_norm or query_norm in alt_names:
        return True
    
    # check hyphenated parts separately
    for part in query_norm.split("-"):
        part = part.strip()
        if len(part) >= 3 and part in name_norm:
            return True
    
    return False


def is_geographic(raw):
    # check result is a real geographic feature
    return raw.get("fcl") in GEOGRAPHIC_CLASSES


def pick_best(results, query):
    # prefer city (P) over region (A) over terrain (T), higher population wins
    valid = [r for r in results if is_geographic(r.raw) and is_valid_match(query, r.raw)]
    if not valid:
        return None
    order = {"P": 0, "A": 1, "T": 2}
    valid.sort(key=lambda r: (order.get(r.raw.get("fcl"), 9), -int(r.raw.get("population", 0))))
    return valid[0]


def split_into_chunks(field):
    # split by ; , : and spaced dashes
    chunks = re.split(r"[;,:]|(?<=\s)-(?=\s)", field)
    return [c.strip() for c in chunks if c.strip() and len(c.strip()) >= 3]


def tokenize_chunk(chunk):
    tokens = []
    for word in chunk.split():
        word = word.strip()
        if not word or len(word) < 5:
            continue
        if not word[0].isupper():  # skip lowercase words - not place names in German
            continue
        if re.match(r"^\d+[\.,]?\d*\s*(m|km)?$", word, re.IGNORECASE):
            continue
        if re.match(r"^\d{1,2}\.\d{1,2}\.\d{4}$", word):
            continue
        tokens.append(word)
    return tokens


def filter_placenames(field, username, country_name=None):
    # get country code from country name
    country_code = get_country_code(country_name, username) if country_name else None

    chunks = split_into_chunks(field)
    locations = {}
    resolved_chunks = []

    for chunk in chunks:
        # strip trailing punctuation before searching
        chunk_clean = chunk.strip(".,;: ")
        
        if not chunk_clean:
            continue
        
        # skip single lowercase words - not place names in German
        if len(chunk_clean.split()) == 1 and not chunk_clean[0].isupper():
            continue

        # try full chunk first
        results = search(chunk_clean, username, country_code)
        hit = pick_best(results, chunk_clean)
        if hit:
            locations[chunk_clean] = {
                "name": hit.raw.get("name"),
                "uri": f"https://sws.geonames.org/{hit.raw.get('geonameId')}/",
                "feature_class": hit.raw.get("fcl"),
                "country_code": hit.raw.get("countryCode"),
                "lat": hit.raw.get("lat"),
                "lng": hit.raw.get("lng"),
            }
            resolved_chunks.append(chunk_clean)
            continue

        # full chunk failed, try word by word
        tokens = tokenize_chunk(chunk_clean)
        for token in tokens:
            results = search(token, username, country_code)
            hit = pick_best(results, token)
            if hit:
                locations[token] = {
                    "name": hit.raw.get("name"),
                    "uri": f"https://sws.geonames.org/{hit.raw.get('geonameId')}/",
                    "feature_class": hit.raw.get("fcl"),
                    "country_code": hit.raw.get("countryCode"),
                    "lat": hit.raw.get("lat"),
                    "lng": hit.raw.get("lng"),
                }
                resolved_chunks.append(token)

    # remove resolved place names from original string
    field_short = field
    for chunk in resolved_chunks:
        field_short = field_short.replace(chunk, "").strip()
    field_short = re.sub(r"[;,:\s]+", " ", field_short).strip()

    return (field_short, locations)