"""
src/data/footprint_utils.py
────────────────────────────
Geospatial utilities for zone footprint generation.
Converts zone center + radius to WKT polygon in the correct UTM zone (44N).
Handles the curvature of Earth properly near Madurai (9.9°N, 78.1°E).
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
from pyproj import Transformer, CRS
from shapely.geometry import Point, Polygon, mapping
from shapely.ops import transform as shapely_transform
from sentinelsat import read_geojson, geojson_to_wkt


# Madurai sits in UTM Zone 44N (EPSG:32644)
UTM_44N = CRS("EPSG:32644")
WGS84   = CRS("EPSG:4326")


def zone_to_wkt(
    lat: float,
    lon: float,
    radius_m: float,
    n_points: int = 64,
) -> str:
    """
    Create a circular WKT footprint around (lat, lon) with exact metric radius.

    Args:
        lat:       Center latitude (decimal degrees, WGS84)
        lon:       Center longitude (decimal degrees, WGS84)
        radius_m:  Radius in meters
        n_points:  Number of polygon vertices (higher = smoother circle)

    Returns:
        WKT string suitable for Sentinel API footprint query
    """
    # Project center to UTM 44N, buffer in meters, project back to WGS84
    to_utm = Transformer.from_crs(WGS84, UTM_44N, always_xy=True)
    to_wgs = Transformer.from_crs(UTM_44N, WGS84, always_xy=True)

    utm_center = Point(*to_utm.transform(lon, lat))
    utm_circle = utm_center.buffer(radius_m, resolution=n_points)

    def reproject(geom):
        return shapely_transform(
            lambda x, y, z=None: to_wgs.transform(x, y),
            geom,
        )

    wgs_circle = reproject(utm_circle)

    # Build GeoJSON Feature Collection and convert to WKT via sentinelsat
    feature_collection = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": mapping(wgs_circle),
                "properties": {},
            }
        ],
    }
    tmp = Path(tempfile.mktemp(suffix=".geojson"))
    tmp.write_text(json.dumps(feature_collection))
    wkt = geojson_to_wkt(read_geojson(str(tmp)))
    tmp.unlink(missing_ok=True)
    return wkt


def kml_to_footprint(kml_path: str) -> str:
    """
    Convert a KML file (single polygon) to WKT for API query.

    Args:
        kml_path: Path to KML file

    Returns:
        WKT string
    """
    try:
        import fiona
    except ImportError:
        raise ImportError("pip install fiona  (required for KML reading)")

    with fiona.open(kml_path, driver="KML") as src:
        features = list(src)

    if not features:
        raise ValueError(f"No features found in {kml_path}")

    geom = shape(features[0]["geometry"])
    feature_collection = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "geometry": mapping(geom), "properties": {}}],
    }
    tmp = Path(tempfile.mktemp(suffix=".geojson"))
    tmp.write_text(json.dumps(feature_collection))
    wkt = geojson_to_wkt(read_geojson(str(tmp)))
    tmp.unlink(missing_ok=True)
    return wkt


def zone_to_bbox(
    lat: float,
    lon: float,
    radius_m: float,
) -> tuple[float, float, float, float]:
    """
    Return (min_lon, min_lat, max_lon, max_lat) bounding box for a zone.
    Useful for map zoom fitting.
    """
    deg_lat = radius_m / 111_000
    deg_lon = radius_m / (111_000 * np.cos(np.radians(lat)))
    return (
        lon - deg_lon,
        lat - deg_lat,
        lon + deg_lon,
        lat + deg_lat,
    )


def meters_to_degrees(meters: float, lat: float) -> tuple[float, float]:
    """Convert meters to approximate degree deltas at given latitude."""
    dlat = meters / 111_000
    dlon = meters / (111_000 * np.cos(np.radians(lat)))
    return dlat, dlon


if __name__ == "__main__":
    from src.data.madurai_zones import all_zones

    for zone in all_zones():
        wkt = zone_to_wkt(zone.lat, zone.lon, zone.radius_m)
        bbox = zone_to_bbox(zone.lat, zone.lon, zone.radius_m)
        print(f"{zone.name}")
        print(f"  WKT prefix: {wkt[:80]}…")
        print(f"  BBox: {[round(c,4) for c in bbox]}")
        print()
