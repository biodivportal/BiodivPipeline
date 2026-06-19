from .cleaner import clean_locality_text
from .place_filter import filter_placenames
from .envo_matching import match_envo

def score(row):
    locality = row.get("Locality", "")
    #fundort = row.get("FundortOeko", "")
    
    locality_short, locations = filter_placenames(locality)
    clean_locality = clean_locality_text(locality_short)

    match = match_envo(clean_locality)

    # Here we can score and decision. and put together the final result for the json

    return dict()
