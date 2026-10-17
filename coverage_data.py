"""Coverage counties shown on the /cobertura page.

Cities are stored in the coverage_cities table and managed from the admin
panel. `default_cities` only seeds that table on first run: the incorporated
cities of each county, taken from the "List of municipalities in California"
(U.S. Census data).

`fips` must match the county ids in static/data/ca_counties.geojson.
"""
import json
import math
import os
from functools import lru_cache

COVERAGE_COUNTIES = [
    {
        "key": "los-angeles",
        "name": "Los Angeles County",
        "fips": "06037",
        "color": "#E7AA35",
        "seat": "Los Angeles",
        "default_cities": [
            "Agoura Hills", "Alhambra", "Arcadia", "Artesia", "Avalon", "Azusa",
            "Baldwin Park", "Bell", "Bell Gardens", "Bellflower", "Beverly Hills",
            "Bradbury", "Burbank", "Calabasas", "Carson", "Cerritos", "City of Industry",
            "Claremont", "Commerce", "Compton", "Covina", "Cudahy", "Culver City",
            "Diamond Bar", "Downey", "Duarte", "El Monte", "El Segundo", "Gardena",
            "Glendale", "Glendora", "Hawaiian Gardens", "Hawthorne", "Hermosa Beach",
            "Hidden Hills", "Huntington Park", "Inglewood", "Irwindale",
            "La Cañada Flintridge", "La Habra Heights", "La Mirada", "La Puente",
            "La Verne", "Lakewood", "Lancaster", "Lawndale", "Lomita", "Long Beach",
            "Los Angeles", "Lynwood", "Malibu", "Manhattan Beach", "Maywood", "Monrovia",
            "Montebello", "Monterey Park", "Norwalk", "Palmdale", "Palos Verdes Estates",
            "Paramount", "Pasadena", "Pico Rivera", "Pomona", "Rancho Palos Verdes",
            "Redondo Beach", "Rolling Hills", "Rolling Hills Estates", "Rosemead",
            "San Dimas", "San Fernando", "San Gabriel", "San Marino", "Santa Clarita",
            "Santa Fe Springs", "Santa Monica", "Sierra Madre", "Signal Hill",
            "South El Monte", "South Gate", "South Pasadena", "Temple City", "Torrance",
            "Vernon", "Walnut", "West Covina", "West Hollywood", "Westlake Village",
            "Whittier",
        ],
    },
    {
        "key": "orange",
        "name": "Orange County",
        "fips": "06059",
        "color": "#D9622B",
        "seat": "Santa Ana",
        "default_cities": [
            "Aliso Viejo", "Anaheim", "Brea", "Buena Park", "Costa Mesa", "Cypress",
            "Dana Point", "Fountain Valley", "Fullerton", "Garden Grove",
            "Huntington Beach", "Irvine", "La Habra", "La Palma", "Laguna Beach",
            "Laguna Hills", "Laguna Niguel", "Laguna Woods", "Lake Forest",
            "Los Alamitos", "Mission Viejo", "Newport Beach", "Orange", "Placentia",
            "Rancho Santa Margarita", "San Clemente", "San Juan Capistrano", "Santa Ana",
            "Seal Beach", "Stanton", "Tustin", "Villa Park", "Westminster", "Yorba Linda",
        ],
    },
    {
        "key": "san-bernardino",
        "name": "San Bernardino County",
        "fips": "06071",
        "color": "#8C5A2B",
        "seat": "San Bernardino",
        "default_cities": [
            "Adelanto", "Apple Valley", "Barstow", "Big Bear Lake", "Chino", "Chino Hills",
            "Colton", "Fontana", "Grand Terrace", "Hesperia", "Highland", "Loma Linda",
            "Montclair", "Needles", "Ontario", "Rancho Cucamonga", "Redlands", "Rialto",
            "San Bernardino", "Twentynine Palms", "Upland", "Victorville", "Yucaipa",
            "Yucca Valley",
        ],
    },
    {
        "key": "riverside",
        "name": "Riverside County",
        "fips": "06065",
        "color": "#4F6D8C",
        "seat": "Riverside",
        "default_cities": [
            "Banning", "Beaumont", "Blythe", "Calimesa", "Canyon Lake", "Cathedral City",
            "Coachella", "Corona", "Desert Hot Springs", "Eastvale", "Hemet",
            "Indian Wells", "Indio", "Jurupa Valley", "La Quinta", "Lake Elsinore",
            "Menifee", "Moreno Valley", "Murrieta", "Norco", "Palm Desert",
            "Palm Springs", "Perris", "Rancho Mirage", "Riverside", "San Jacinto",
            "Temecula", "Wildomar",
        ],
    },
    {
        "key": "ventura",
        "name": "Ventura County",
        "fips": "06111",
        "color": "#6E8B3D",
        "seat": "Ventura",
        "default_cities": [
            "Camarillo", "Fillmore", "Moorpark", "Ojai", "Oxnard", "Port Hueneme",
            "Santa Paula", "Simi Valley", "Thousand Oaks", "Ventura",
        ],
    },
    {
        "key": "santa-barbara",
        "name": "Santa Barbara County",
        "fips": "06083",
        "color": "#8A4F7D",
        "seat": "Santa Barbara",
        "default_cities": [
            "Buellton", "Carpinteria", "Goleta", "Guadalupe", "Lompoc", "Santa Barbara",
            "Santa Maria", "Solvang",
        ],
    },
]


COUNTIES_BY_KEY = {c["key"]: c for c in COVERAGE_COUNTIES}

GEOJSON_PATH = os.path.join(os.path.dirname(__file__), "static", "data", "ca_counties.geojson")


def _ring_area(ring):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]))) / 2


@lru_cache(maxsize=1)
def county_silhouettes(size=100, padding=4):
    """SVG path (viewBox 0 0 size size) of each coverage county's mainland shape.

    Small offshore islands are dropped so the outline stays recognizable.
    """
    with open(GEOJSON_PATH, encoding="utf-8") as fh:
        features = {f["id"]: f for f in json.load(fh)["features"]}

    paths = {}
    for county in COVERAGE_COUNTIES:
        geom = features[county["fips"]]["geometry"]
        polygons = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        rings = [poly[0] for poly in polygons]
        largest = max(_ring_area(r) for r in rings)
        rings = [r for r in rings if _ring_area(r) >= largest * 0.05]

        lat0 = math.radians(sum(lat for r in rings for _, lat in r) / sum(len(r) for r in rings))
        projected = [[(lon * math.cos(lat0), -lat) for lon, lat in r] for r in rings]
        xs = [x for r in projected for x, _ in r]
        ys = [y for r in projected for _, y in r]
        span = max(max(xs) - min(xs), max(ys) - min(ys))
        scale = (size - 2 * padding) / span
        off_x = (size - (max(xs) - min(xs)) * scale) / 2
        off_y = (size - (max(ys) - min(ys)) * scale) / 2

        parts = []
        for r in projected:
            pts = [f"{(x - min(xs)) * scale + off_x:.1f},{(y - min(ys)) * scale + off_y:.1f}" for x, y in r]
            parts.append("M" + "L".join(pts) + "Z")
        paths[county["key"]] = "".join(parts)
    return paths


def seed_coverage_cities():
    """Fill the coverage_cities table with the default lists (first run only)."""
    from extensions import db
    from models import CoverageCity

    if CoverageCity.query.first():
        return
    for county in COVERAGE_COUNTIES:
        for name in county["default_cities"]:
            db.session.add(CoverageCity(county_key=county["key"], name=name, active=True))
    db.session.commit()


def get_coverage_counties(include_inactive=False):
    """Counties with their cities from the database, sorted by city name.

    Public page: `cities` holds the active city names.
    Admin page (include_inactive=True): `city_rows` holds every CoverageCity row.
    """
    from models import CoverageCity

    query = CoverageCity.query
    if not include_inactive:
        query = query.filter_by(active=True)
    rows_by_county = {}
    for row in query.order_by(CoverageCity.name).all():
        rows_by_county.setdefault(row.county_key, []).append(row)

    counties = []
    for county in COVERAGE_COUNTIES:
        rows = rows_by_county.get(county["key"], [])
        data = {k: v for k, v in county.items() if k != "default_cities"}
        data["cities"] = [r.name for r in rows if r.active]
        if include_inactive:
            data["city_rows"] = rows
        counties.append(data)
    return counties
