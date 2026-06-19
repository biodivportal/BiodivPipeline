# from clients.geonames_client import # your function

def filter_placenames(field):
    """ Uses the geonames client to clean the string
    Args:
        field (str): the full unresolved locality string
    Return:
        field_short (str): the string without the place names
        dict locations: the URIs and names of the places found (why not just return it all
    """
    field_short = ""
    locations = dict()
    return (field_short, locations)
