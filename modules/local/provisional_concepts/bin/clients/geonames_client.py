"""
This script should just run words/strings through geonames and return the results, the logic is in the locality package
"""
from geopy.geocoders import GeoNames
from geopy.exc import GeocoderTimedOut
import time

MAX_RETRIES = 3


def get_country_code(country_name, username):
    # convert country name to ISO code
    if not country_name:
        return None
    try:
        geolocator = GeoNames(username=username)
        result = geolocator.geocode(country_name)
        if result:
            return result.raw.get("countryCode")
        return None
    except Exception:
        return None


def search(query, username, country_code=None):
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
            # catch all errors including connection errors
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"[error] GeoNames failed for '{query}': {e}")
                return []