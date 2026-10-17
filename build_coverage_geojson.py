"""Regenerate static/data/ca_counties.geojson (California county boundaries).

Source: U.S. Census Bureau cartographic boundary file (1:500k), as published
in GeoJSON by Plotly. Only California (state FIPS 06) is kept and coordinates
are rounded to 4 decimals (~11 m) to keep the file light for mobile.

Usage:
    py build_coverage_geojson.py
"""
import json
import os
import urllib.request

SOURCE_URL = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
OUTPUT = os.path.join(os.path.dirname(__file__), "static", "data", "ca_counties.geojson")
PRECISION = 4


def _round_ring(ring):
    out = []
    for lon, lat, *_ in ring:
        point = [round(lon, PRECISION), round(lat, PRECISION)]
        if not out or out[-1] != point:
            out.append(point)
    return out


def _round_geometry(geom):
    if geom["type"] == "Polygon":
        coords = [_round_ring(r) for r in geom["coordinates"]]
    elif geom["type"] == "MultiPolygon":
        coords = [[_round_ring(r) for r in poly] for poly in geom["coordinates"]]
    else:
        raise ValueError(f"Unexpected geometry type: {geom['type']}")
    return {"type": geom["type"], "coordinates": coords}


def main():
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "TecunsRoofing/1.0"})
    with urllib.request.urlopen(request) as resp:
        data = json.load(resp)

    features = [
        {
            "type": "Feature",
            "id": f["id"],
            "properties": {"fips": f["id"], "name": f"{f['properties']['NAME']} County"},
            "geometry": _round_geometry(f["geometry"]),
        }
        for f in data["features"]
        if f["properties"]["STATE"] == "06"
    ]
    features.sort(key=lambda f: f["id"])

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as fh:
        json.dump({"type": "FeatureCollection", "features": features}, fh, separators=(",", ":"))

    print(f"{len(features)} counties -> {OUTPUT} ({os.path.getsize(OUTPUT) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
