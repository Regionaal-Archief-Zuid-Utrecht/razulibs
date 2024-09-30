from pyproj import Transformer


# Code specifiek voor de demo-conversie.


# geo-zaken

# Initialiseer de transformer van RD naar WGS84
transformer = Transformer.from_crs("EPSG:28992", "EPSG:4326")


# Functie om een coördinaat-string te parsen
def parse_rd_coord(coord_string):
    parts = coord_string.split()
    rd_x = int(parts[1]) / 1000
    rd_y = int(parts[3]) / 1000
    return rd_x, rd_y

# Functie om RD naar WGS84 om te zetten


def rd_to_wgs84(rd_x, rd_y):
    lon, lat = transformer.transform(rd_x, rd_y)
    return lon, lat


# Functie om een POLYGON te maken van RD naar WGS84
def create_polygon(rd_coord_lu, rd_coord_rb):
    # Parse de coördinaten
    x1, y1 = parse_rd_coord(rd_coord_lu)  # Linksonder
    x2, y2 = parse_rd_coord(rd_coord_rb)  # Rechtsboven

    # Omzetten naar WGS84
    lat1, lon1 = rd_to_wgs84(x1, y1)
    lat2, lon2 = rd_to_wgs84(x2, y2)

    # POLYGON-notatie maken
    polygon = f"POLYGON(({lon1} {lat1}, {lon2} {lat1}, {lon2} {lat2}, {lon1} {lat2}, {lon1} {lat1}))"
    return polygon

###


# Functie om het gewenste formaat te genereren
def maak_bestandsnaam(doosnummer, volgnummer):
    # Splits het doosnummer in jaar en nummer
    jaar, nummer = doosnummer.split('-')
    # Zorg dat het nummer altijd twee posities heeft
    nummer = nummer.zfill(2)
    # Zorg dat volgnummer altijd drie posities heeft
    volgnummer = str(volgnummer).zfill(3)
    # Combineer en retourneer het resultaat
    return f"{jaar}_{nummer}_{volgnummer}.jpg"
