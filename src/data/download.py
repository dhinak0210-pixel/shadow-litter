"""
src/data/download.py
────────────────────
Sentinel-2 ingestion ritual.
Downloads Level-2A imagery for the Madurai AOI from
ESA Copernicus Open Access Hub (or Dataspace).
"""
from __future__ import annotations

import os
import logging
from pathlib import Path
from datetime import date

import yaml
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
from shapely.geometry import Point, mapping
import json

logger = logging.getLogger(__name__)


# ── helpers ──────────────────────────────────────────────────────────────────

def load_config(path: str = "configs/config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def aoi_to_wkt(lat: float, lon: float, buffer_km: float) -> str:
    """Create a circular WKT polygon around (lat, lon) with buffer_km radius."""
    # approx degrees per km at given lat
    deg = buffer_km / 111.0
    point = Point(lon, lat)
    poly = point.buffer(deg)
    geojson = mapping(poly)
    # write temp file, read back via sentinelsat utility
    tmp = Path("/tmp/shadow_aoi.geojson")
    tmp.write_text(json.dumps({"type": "FeatureCollection",
                               "features": [{"type": "Feature",
                                             "geometry": geojson,
                                             "properties": {}}]}))
    return geojson_to_wkt(read_geojson(str(tmp)))


# ── main download routine ─────────────────────────────────────────────────────

def download_sentinel2(config_path: str = "configs/config.yaml") -> None:
    cfg = load_config(config_path)
    s_cfg = cfg["sentinel"]
    p_cfg = cfg["paths"]
    proj = cfg["project"]

    user = os.environ.get("SENTINEL_USER", s_cfg.get("username", ""))
    password = os.environ.get("SENTINEL_PASS", s_cfg.get("password", ""))

    if not user or not password:
        raise EnvironmentError(
            "Set SENTINEL_USER and SENTINEL_PASS environment variables "
            "or fill in configs/config.yaml"
        )

    raw_dir = Path(p_cfg["raw"])
    raw_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Connecting to Copernicus Open Access Hub …")
    api = SentinelAPI(user, password, s_cfg["api_url"])

    footprint = aoi_to_wkt(
        proj["aoi_lat"], proj["aoi_lon"], proj["aoi_buffer_km"]
    )

    logger.info(f"Querying {s_cfg['platform']} products for Madurai AOI …")
    products = api.query(
        footprint,
        date=(s_cfg["date_start"], s_cfg["date_end"]),
        platformname=s_cfg["platform"],
        producttype=s_cfg["product_type"],
        cloudcoverpercentage=(0, s_cfg["cloud_cover_max"]),
    )

    logger.info(f"Found {len(products)} products. Downloading to {raw_dir} …")
    api.download_all(products, directory_path=str(raw_dir))
    logger.info("✅ Download complete.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    download_sentinel2()
