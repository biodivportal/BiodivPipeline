"""
Client for geonames, uses local geonames dataset and fallsback to the API through geocoder
The local results might not match the geonames API
"""
from geopy.geocoders import GeoNames
from geopy.exc import GeocoderTimedOut
import time
from clients.local_geonames import LocalGeoNames

MAX_RETRIES = 3


def get_country_code(country_name, username=None):
    # convert country name to ISO code, tries local first then API
    if not country_name:
        return None
    local_geocoder = LocalGeoNames()
    result = local_geocoder.geocode(country_name)
    if result:
        return result.raw.get("countryCode")
    try:
        geolocator = GeoNames(username=username)
        result = geolocator.geocode(country_name)
        if result:
            return result.raw.get("countryCode")
        return None
    except Exception:
        return None


def search(query, username=None, country_code=None):
    # search local data first, fallback to API if nothing found
    local_geocoder = LocalGeoNames()
    local_results = local_geocoder.geocode(query, exactly_one=False, country=country_code)
    if local_results:
        return local_results
    if not username:
        return []
    geolocator = GeoNames(username=username)
    for attempt in range(MAX_RETRIES):
        try:
            results = geolocator.geocode(query, exactly_one=False, country=country_code)
            return results or []
        except GeocoderTimedOut:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"[error] GeoNames timed out for '{query}'")
                return []
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"[error] GeoNames failed for '{query}': {e}")
                return []


# ---- Previous implementation v1 - local DE.txt with in-memory index ----
# Used before David's local_geonames.py was available
# Achieved 97.3% resolution on 20k rows
#
# import csv
# import threading
# _lock = threading.Lock()
# _data = []
# _index = {}
# GEONAMEID, NAME, ASCIINAME, ALTERNATENAMES = 0, 1, 2, 3
# LAT, LNG, FEATURE_CLASS, FEATURE_CODE, COUNTRY_CODE, POPULATION = 4, 5, 6, 7, 8, 14
#
# def load_local_data(filepath=None):
#     global _data, _index
#     with _lock:
#         if _data:
#             return
#         with open(filepath, encoding="utf-8") as f:
#             reader = csv.reader(f, delimiter="\t")
#             for row in reader:
#                 if len(row) > 14:
#                     _data.append(row)
#                     for key in [row[NAME].lower(), row[ASCIINAME].lower()]:
#                         if key not in _index:
#                             _index[key] = []
#                         _index[key].append(row)
#
# def search(query, username=None, country_code=None):
#     if not _data:
#         load_local_data()
#     query_lower = query.lower()
#     results = []
#     seen = set()
#     for key, rows in _index.items():
#         if query_lower in key or key in query_lower:
#             for row in rows:
#                 if row[GEONAMEID] not in seen:
#                     if not country_code or row[COUNTRY_CODE] == country_code:
#                         seen.add(row[GEONAMEID])
#                         results.append({
#                             "geonameId": row[GEONAMEID],
#                             "name": row[NAME],
#                             "asciiName": row[ASCIINAME],
#                             "alternateNames": row[ALTERNATENAMES],
#                             "lat": row[LAT],
#                             "lng": row[LNG],
#                             "fcl": row[FEATURE_CLASS],
#                             "fcode": row[FEATURE_CODE],
#                             "countryCode": row[COUNTRY_CODE],
#                             "population": int(row[POPULATION]) if row[POPULATION].isdigit() else 0,
#                         })
#     return results