"""
This script should just run words/strings through geonames and return the results, the logic is in the locality package
"""

import csv
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading
_lock = threading.Lock()

# column indices in DE.txt
GEONAMEID = 0
NAME = 1
ASCIINAME = 2
ALTERNATENAMES = 3
LAT = 4
LNG = 5
FEATURE_CLASS = 6
FEATURE_CODE = 7
COUNTRY_CODE = 8
POPULATION = 14

# loaded data and index
_data = []
_index = {}  # name -> list of rows for fast lookup


def load_local_data(filepath=None):
    global _data, _index
    with _lock:
        if _data:
            return
        if filepath is None:
            filepath = Path(__file__).parent.parent / "data" / "DE.txt"
        with open(filepath, encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                if len(row) > 14:
                    _data.append(row)
                    for key in [row[NAME].lower(), row[ASCIINAME].lower()]:
                        if key not in _index:
                            _index[key] = []
                        _index[key].append(row)
        print(f"[info] Loaded {len(_data)} GeoNames records")


def get_country_code(country_name, username=None):
    if not _data:
        load_local_data()
    if not country_name:
        return None
    country_lower = country_name.lower()
    for row in _data:
        if row[FEATURE_CODE] == "PCLI" and country_lower in row[NAME].lower():
            return row[COUNTRY_CODE]
    return None


def search(query, username=None, country_code=None):
    if not _data:
        load_local_data()

    query_lower = query.lower()
    results = []
    seen = set()

    # fast lookup using index
    for key, rows in _index.items():
        if query_lower in key or key in query_lower:
            for row in rows:
                if row[GEONAMEID] not in seen:
                    if not country_code or row[COUNTRY_CODE] == country_code:
                        seen.add(row[GEONAMEID])
                        results.append({
                            "geonameId": row[GEONAMEID],
                            "name": row[NAME],
                            "asciiName": row[ASCIINAME],
                            "alternateNames": row[ALTERNATENAMES],
                            "lat": row[LAT],
                            "lng": row[LNG],
                            "fcl": row[FEATURE_CLASS],
                            "fcode": row[FEATURE_CODE],
                            "countryCode": row[COUNTRY_CODE],
                            "population": int(row[POPULATION]) if row[POPULATION].isdigit() else 0,
                        })

    return results

# MAX_RETRIES = 3


# def get_country_code(country_name, username):
#     # convert country name to ISO code
#     if not country_name:
#         return None
#     try:
#         geolocator = GeoNames(username=username)
#         result = geolocator.geocode(country_name)
#         if result:
#             return result.raw.get("countryCode")
#         return None
#     except Exception:
#         return None


# def search(query, username, country_code=None):
#     geolocator = GeoNames(username=username)
#     for attempt in range(MAX_RETRIES):
#         try:
#             results = geolocator.geocode(query, exactly_one=False, country=country_code)
#             return results or []
#         except GeocoderTimedOut:
#             if attempt < MAX_RETRIES - 1:
#                 time.sleep(2 ** attempt)
#             else:
#                 print(f"[error] GeoNames timed out for '{query}'")
#                 return []
#         except Exception as e:
#             # catch all errors including connection errors
#             if attempt < MAX_RETRIES - 1:
#                 time.sleep(2 ** attempt)
#             else:
#                 print(f"[error] GeoNames failed for '{query}': {e}")
#                 return []




