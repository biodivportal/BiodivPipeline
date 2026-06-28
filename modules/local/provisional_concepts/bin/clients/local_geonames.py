from pathlib import Path
import urllib.request
import zipfile
from rapidfuzz import process, fuzz
from geopy.geocoders.base import Geocoder
from geopy.location import Location

DATA_DIR = Path(__file__).parent.parent / "geonames_data"

_lookup_dict = None


class LocalGeoNames(Geocoder):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def geocode(self, query, *, exactly_one=True, timeout=None, country=None):
        results = local_lookup(query, country_code=country)
        if not results:
            return None

        locations = []
        for r in results:
            placename = r.get("name", "")
            state = r.get("adminName1", None)
            country_name = r.get("countryName", None)

            address = ", ".join([x for x in [placename, state, country_name] if x])

            lat = float(r.get("lat") or 0.0)
            lng = float(r.get("lng") or 0.0)

            loc = Location(address, (lat, lng), r)
            locations.append(loc)

        if exactly_one:
            return locations[0]
        return locations


def download_country_data(country_code):
    cc = country_code.upper()
    txt_file = DATA_DIR / f"{cc}.txt"
    if txt_file.exists():
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    zip_file = DATA_DIR / f"{cc}.zip"
    url = f"https://download.geonames.org/export/dump/{cc}.zip"

    print(f"Downloading GeoNames data for {cc}...")
    try:
        urllib.request.urlretrieve(url, zip_file)
        with zipfile.ZipFile(zip_file, "r") as z:
            z.extract(f"{cc}.txt", DATA_DIR)
        zip_file.unlink()
    except Exception as e:
        print(f"Error downloading country data for {cc}: {e}")


def load_admin1_codes():
    admin1_map = {}
    admin1_file = DATA_DIR / "admin1CodesASCII.txt"
    if not admin1_file.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        url = "https://download.geonames.org/export/dump/admin1CodesASCII.txt"
        print("Downloading admin1 codes mapping...")
        try:
            urllib.request.urlretrieve(url, admin1_file)
        except Exception as e:
            print(f"Error downloading admin1 codes: {e}")
            return admin1_map

    try:
        with open(admin1_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t")
                admin1_map[parts[0]] = parts[1]
    except Exception:
        pass
    return admin1_map


def load_data():
    global _lookup_dict
    if _lookup_dict is not None:
        return

    _lookup_dict = {}

    download_country_data("DE")

    admin1_map = load_admin1_codes()
    for txt_file in DATA_DIR.glob("*.txt"):
        if txt_file.name == "admin1CodesASCII.txt":
            continue
        try:
            with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split("\t")

                    alt_names = (
                        [{"name": x.strip()} for x in parts[3].split(",") if x.strip()]
                        if parts[3]
                        else []
                    )

                    admin_name1 = admin1_map.get(f"{parts[8]}.{parts[10]}", "")

                    record = {
                        "geonameId": int(parts[0]),
                        "name": parts[1],
                        "toponymName": parts[2],
                        "alternateNames": alt_names,
                        "lat": parts[4],
                        "lng": parts[5],
                        "fcl": parts[6],
                        "fcode": parts[7],
                        "countryCode": parts[8],
                        "countryName": parts[8],
                        "adminCode1": parts[10],
                        "adminName1": admin_name1,
                        "adminCode2": parts[11],
                        "population": int(parts[14]) if parts[14] else 0,
                    }

                    keys = {
                        k.lower()
                        for k in [parts[1], parts[2]] + [x["name"] for x in alt_names]
                        if k
                    }

                    for key in keys:
                        if key not in _lookup_dict:
                            _lookup_dict[key] = []
                        _lookup_dict[key].append(record)
        except Exception as e:
            print(f"Error loading the Geonames data: {e}")
            pass

# 73 seec for 100
# def local_lookup(query, country_code=None):
#     load_data()
#     if not query:
#         return []

#     q_lower = query.lower()
#     choices = list(_lookup_dict.keys())

#     matches = process.extract(
#         q_lower, choices, scorer=fuzz.partial_ratio, limit=100, score_cutoff=80.0
#     )

#     records = []
#     for matched_key, score, _ in matches:
#         for r in _lookup_dict[matched_key]:
#             r_score = r.copy()
#             r_score["_score"] = score
#             records.append(r_score)

#     records.sort(key=lambda r: (-r["_score"], -int(r.get("population", 0))))

#     if country_code:
#         records = [
#             r
#             for r in records
#             if r.get("countryCode", "").upper() == country_code.upper()
#         ]

#     return records

# 48.2 sec for 100
# def local_lookup(query, country_code=None):
#     load_data()
#     if not query:
#         return []

#     q_lower = query.lower()

#     # try exact match first - instant lookup
#     if q_lower in _lookup_dict:
#         records = _lookup_dict[q_lower]
#         if country_code:
#             records = [r for r in records if r.get("countryCode", "").upper() == country_code.upper()]
#         if records:
#             records = sorted(records, key=lambda r: -int(r.get("population", 0)))
#             return records

#     # fallback to rapidfuzz for fuzzy matching (handles typos/umlauts)
#     choices = list(_lookup_dict.keys())
#     matches = process.extract(
#         q_lower, choices, scorer=fuzz.partial_ratio, limit=100, score_cutoff=80.0
#     )

#     records = []
#     for matched_key, score, _ in matches:
#         for r in _lookup_dict[matched_key]:
#             r_score = r.copy()
#             r_score["_score"] = score
#             records.append(r_score)

#     records.sort(key=lambda r: (-r["_score"], -int(r.get("population", 0))))

#     if country_code:
#         records = [
#             r
#             for r in records
#             if r.get("countryCode", "").upper() == country_code.upper()
#         ]

#     return records

# 9 secs for 100, 93 sec for 1k, 964/1000
def local_lookup(query, country_code=None):
    load_data()
    if not query:
        return []

    q_lower = query.lower()

    # 1. exact match first - instant
    if q_lower in _lookup_dict:
        records = _lookup_dict[q_lower]
        if country_code:
            records = [r for r in records if r.get("countryCode", "").upper() == country_code.upper()]
        if records:
            return sorted(records, key=lambda r: -int(r.get("population", 0)))

    # 2. substring match - faster than rapidfuzz
    records = []
    seen = set()
    for key, rows in _lookup_dict.items():
        if q_lower in key or key in q_lower:
            for r in rows:
                rid = r.get("geonameId")
                if rid not in seen:
                    seen.add(rid)
                    if not country_code or r.get("countryCode","").upper() == country_code.upper():
                        records.append(r)
    
    if records:
        return sorted(records, key=lambda r: -int(r.get("population", 0)))

    # 3. rapidfuzz only as last resort
    choices = list(_lookup_dict.keys())
    matches = process.extract(q_lower, choices, scorer=fuzz.partial_ratio, limit=100, score_cutoff=80.0)
    records = []
    for matched_key, score, _ in matches:
        for r in _lookup_dict[matched_key]:
            r_score = r.copy()
            r_score["_score"] = score
            records.append(r_score)
    records.sort(key=lambda r: (-r["_score"], -int(r.get("population", 0))))
    if country_code:
        records = [r for r in records if r.get("countryCode","").upper() == country_code.upper()]
    return records