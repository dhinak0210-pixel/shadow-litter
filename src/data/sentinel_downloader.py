"""
src/data/sentinel_downloader.py
────────────────────────────────
SentinelOracle — queries and downloads Sentinel-2 Level-2A imagery
from ESA Copernicus Open Access Hub.

Authentication: uses guest/guest public credentials by default.
For bulk downloads, register free at: https://scihub.copernicus.eu/
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import rasterio
from rasterio.merge import merge
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
from shapely.geometry import Point, mapping, shape
import json
import numpy as np

from src.data.madurai_zones import Zone
from src.data.footprint_utils import zone_to_wkt

logger = logging.getLogger(__name__)


class SentinelOracle:
    """
    Queries and downloads Sentinel-2 imagery for Madurai waste zones.

    Usage:
        oracle = SentinelOracle()
        products = oracle.query_zone(zone, '2023-01-01', '2023-12-31')
        for pid, meta in list(products.items())[:5]:
            oracle.download_product(pid, output_dir='data/raw/sentinel/vaigai')
    """

    COPERNICUS_URL = "https://apihub.copernicus.eu/apihub"

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self.username = username or os.environ.get("SENTINEL_USER", "guest")
        self.password = password or os.environ.get("SENTINEL_PASS", "guest")
        logger.info(f"Connecting to Copernicus Hub as '{self.username}' …")
        self.api = SentinelAPI(self.username, self.password, self.COPERNICUS_URL)
        logger.info("✅ Connection established.")

    # ── Query ─────────────────────────────────────────────────────────────────

    def query_zone(
        self,
        zone: Zone,
        start_date: str,
        end_date: str,
        max_cloud: int = 20,
    ) -> dict:
        """
        Query available Sentinel-2 L2A products for a zone and date range.

        Args:
            zone:       Zone dataclass from madurai_zones
            start_date: ISO date string "YYYY-MM-DD"
            end_date:   ISO date string "YYYY-MM-DD"
            max_cloud:  Max cloud cover percentage

        Returns:
            OrderedDict of {product_id: metadata}
        """
        footprint = zone_to_wkt(zone.lat, zone.lon, zone.radius_m)
        logger.info(
            f"[{zone.name}] Querying {start_date} → {end_date} "
            f"(cloud ≤ {max_cloud}%) …"
        )
        products = self.api.query(
            footprint,
            date=(start_date, end_date),
            platformname="Sentinel-2",
            producttype="S2MSI2A",
            cloudcoverpercentage=(0, max_cloud),
        )
        logger.info(f"[{zone.name}] {len(products)} products found.")
        return products

    def sort_by_cloud(self, products: dict) -> list[tuple]:
        """Return products sorted by cloud cover (lowest first)."""
        gdf = self.api.to_geodataframe(products)
        gdf = gdf.sort_values("cloudcoverpercentage")
        return [(row.Index, row) for row in gdf.itertuples()]

    # ── Download ──────────────────────────────────────────────────────────────

    def download_product(
        self,
        product_id: str,
        output_dir: str = "data/raw/sentinel",
    ) -> Path:
        """
        Download a single Sentinel-2 product to output_dir.

        Returns path to downloaded .SAFE folder.
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading product {product_id} → {out} …")
        self.api.download(product_id, directory_path=str(out))

        # Find the downloaded .SAFE folder
        safe_dirs = list(out.glob("*.SAFE"))
        if safe_dirs:
            logger.info(f"✅ Downloaded: {safe_dirs[-1].name}")
            return safe_dirs[-1]
        raise RuntimeError(f"Download finished but no .SAFE found in {out}")

    def download_zone_top_n(
        self,
        zone: Zone,
        start_date: str,
        end_date: str,
        n: int = 5,
        output_dir: Optional[str] = None,
        max_cloud: int = 20,
    ) -> list[Path]:
        """Download the N clearest images for a zone."""
        if output_dir is None:
            output_dir = f"data/raw/sentinel/{zone.name}"

        products = self.query_zone(zone, start_date, end_date, max_cloud)
        sorted_products = self.sort_by_cloud(products)

        paths = []
        for pid, meta in sorted_products[:n]:
            try:
                path = self.download_product(str(pid), output_dir)
                paths.append(path)
            except Exception as e:
                logger.warning(f"  Failed to download {pid}: {e}")
        return paths

    # ── Convert ───────────────────────────────────────────────────────────────

    def convert_to_geotiff(
        self,
        safe_folder: Path,
        bands: list[str] = ("B02", "B03", "B04", "B08", "B11", "B12"),
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Stack selected bands from a .SAFE folder into a single multi-band GeoTIFF.

        Args:
            safe_folder:  Path to .SAFE directory
            bands:        Band names to include (order determines channel index)
            output_path:  Where to write the GeoTIFF (auto-named if None)

        Returns:
            Path to output GeoTIFF
        """
        safe_folder = Path(safe_folder)

        BAND_GLOB = {
            "B02": "*B02_10m.jp2",
            "B03": "*B03_10m.jp2",
            "B04": "*B04_10m.jp2",
            "B08": "*B08_10m.jp2",
            "B11": "*B11_20m.jp2",
            "B12": "*B12_20m.jp2",
        }

        band_files = {}
        for band in bands:
            matches = list(safe_folder.rglob(BAND_GLOB[band]))
            if not matches:
                raise FileNotFoundError(f"Band {band} not found in {safe_folder}")
            band_files[band] = matches[0]

        # Use B04 (Red, 10m) as reference spatial extent
        with rasterio.open(band_files.get("B04", list(band_files.values())[0])) as ref:
            meta = ref.meta.copy()
            H, W = ref.height, ref.width

        meta.update(count=len(bands), dtype="float32", driver="GTiff")

        if output_path is None:
            stem = safe_folder.stem.split("_MSIL2A_")[1][:15] if "_MSIL2A_" in safe_folder.stem else safe_folder.stem
            output_path = safe_folder.parent / f"{stem}_stacked.tif"

        with rasterio.open(output_path, "w", **meta) as dst:
            for i, band in enumerate(bands, start=1):
                with rasterio.open(band_files[band]) as src:
                    data = src.read(
                        1,
                        out_shape=(H, W),
                        resampling=rasterio.enums.Resampling.bilinear,
                    ).astype("float32")
                dst.write(data, i)

        logger.info(f"✅ GeoTIFF written: {output_path}  ({len(bands)} bands, {H}×{W}px)")
        return Path(output_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.data.madurai_zones import get_zone

    oracle = SentinelOracle()
    zone = get_zone("vaigai_riverbed")
    products = oracle.query_zone(zone, "20240101", "20240630", max_cloud=15)
    sorted_p = oracle.sort_by_cloud(products)
    if sorted_p:
        pid, meta = sorted_p[0]
        print(f"\nClearest product: {meta.title}")
        print(f"  Cloud cover:  {meta.cloudcoverpercentage:.1f}%")
        print(f"  Date:         {meta.beginposition.date()}")
        print(f"  Size:         {meta.size}")
        print(f"\nTo download: oracle.download_product('{pid}', 'data/raw/sentinel/vaigai')")
