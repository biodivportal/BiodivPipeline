import pygbif
from pygbif import species


pygbif.caching(True)

def species_match(row):
    fullname = row["example_FullNameCache"]
    name = row["example_NameCache"]
    genus = row["example_Genus"]
    family = row["example_Family"]

    res = species.name_backbone(scientificName=fullname, family=family, genus=genus)
    usage = res.get("usage")
    classification = res.get("classification")
    diagnostics = res.get("diagnostics")
    synonym = res.get("synonym")

    if not diagnostics["matchType"] :
        print(f"No match found for {fullname}")

    return res
    #return usage, classification, diagnostics, synonym
