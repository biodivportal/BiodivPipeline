import pygbif
from pygbif import species

pygbif.caching(True)


def species_match(source_taxonomy, scientific_name, target_rank=None):
    family = source_taxonomy.get("family")
    genus = source_taxonomy.get("genus")

    return species.name_backbone(
        scientificName=scientific_name,
        family=family,
        genus=genus,
        taxonRank=target_rank,
    )
