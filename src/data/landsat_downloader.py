"""
src/data/landsat_downloader.py
───────────────────────────────
LandsatWitness — queries and downloads Landsat 8/9 thermal imagery
from USGS EarthExplorer via the landsatxplore library.

Band 10 (TIRS Thermal Infrared) reveals heat signatures:
  - Normal soil/vegetation: ~295-305K
  - Active dump sites: ~310-325K (methane decomposition)
  - Water bodies: ~290-300K (reference)

Install:
    pip install landsatxplore
    
Register free at: https://ers.cr.usgs.gov/register
"""
from __future__ import annotations

import logging
import os
import tarfile
from pathlib import Path
from typing import Optional

import numpy as np

from src.data.madurai_zones import Zone
from src.data.footprint_utils import zone_to_bbox

logger = logging.getLogger(__name__)


class LandsatWitness:
    """
    Downloads Landsat 8/9 thermal scenes for Madurai waste zones.

    The thermal witness sees what optical sensors miss:
    hot spots that persist through cloud cover and across seasons.
    """

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        try:
            from landsatxplore.api import API
            from landsatxplore.earthexplorer import EarthExplorer
        except ImportError:
            raise ImportError(
                "pip install landsatxplore\n"
                "Register free at https://ers.cr.usgs.gov/register"
            )

        self.username = username or os.environ.get("USGS_USER", "")
        self.password = password or os.environ.get("USGS_PASS", "")

        if not self.username or not self.password:
            raise EnvironmentError(
                "Set USGS_USER and USGS_PASS environment variables.\n"
                "Register free at https://ers.cr.usgs.gov/register"
            )

        from landsatxplore.api import API
        from landsatxplore.earthexplorer import EarthExplorer
        self._API = API
        self._EE  = EarthExplorer

    # ── Query ─────────────────────────────────────────────────────────────────

    def query_thermal(
        self,
        zone: Zone,
        start_date: str,
        end_date: str,
        max_cloud: int = 30,
        dataset: str = "landsat_ot_c2_l2",   # Collection 2 Level-2
    ) -> list[dict]:
        """
        Query Landsat scenes covering a zone and date range.

        Args:
            zone:       Zone dataclass
            start_date: "YYYY-MM-DD"
            end_date:   "YYYY-MM-DD"
            max_cloud:  Max cloud cover %
            dataset:    USGS dataset identifier

        Returns:
            List of scene metadata dicts
        """
        api = self._API(self.username, self.password)
        try:
            min_lon, min_lat, max_lon, max_lat = zone_to_bbox(
                zone.lat, zone.lon, zone.radius_m
            )
            logger.info(f"[{zone.name}] Querying Landsat {start_date}→{end_date} …")
            scenes = api.search(
                dataset=dataset,
                latitude=zone.lat,
                longitude=zone.lon,
                start_date=start_date,
                end_date=end_date,
                max_cloud_cover=max_cloud,
                max_results=20,
            )
            logger.info(f"[{zone.name}] {len(scenes)} Landsat scenes found.")
            return scenes
        finally:
            api.logout()

    # ── Download ──────────────────────────────────────────────────────────────

    def download_scene(
        self,
        scene_id: str,
        output_dir: str = "data/raw/landsat",
    ) -> Path:
        """Download a single Landsat scene by entity ID."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        ee = self._EE(self.username, self.password)
        try:
            logger.info(f"Downloading Landsat scene {scene_id} → {out} …")
            ee.download(scene_id, output_dir=str(out))
            # Find extracted directory
            dirs = sorted(out.iterdir(), key=lambda p: p.stat().st_mtime)
            logger.info(f"✅ Downloaded: {dirs[-1].name}")
            return dirs[-1]
        finally:
            ee.logout()

    # ── Band 10 extraction ────────────────────────────────────────────────────

    def extract_thermal_band(
        self,
        scene_dir: Path,
        output_path: Optional[Path] = None,
    ) -> tuple[Path, "np.ndarray"]:
        """
        Extract Band 10 (TIRS thermal) from a Landsat scene.
        Converts raw DN to brightness temperature (Kelvin).

        Returns:
            (output_tif_path, brightness_temperature_array)
        """
        import rasterio
        scene_dir = Path(scene_dir)

        # Find B10 file
        b10_files = list(scene_dir.glob("*B10.TIF"))
        if not b10_files:
            raise FileNotFoundError(f"Band 10 not found in {scene_dir}")
        b10_path = b10_files[0]

        # Find MTL metadata for DN → radiance → temperature conversion
        mtl_files = list(scene_dir.glob("*MTL.txt"))
        if not mtl_files:
            raise FileNotFoundError(f"MTL metadata not found in {scene_dir}")

        constants = self._parse_mtl(mtl_files[0])
        ML = constants["RADIANCE_MULT_BAND_10"]
        AL = constants["RADIANCE_ADD_BAND_10"]
        K1 = constants["K1_CONSTANT_BAND_10"]
        K2 = constants["K2_CONSTANT_BAND_10"]

        with rasterio.open(b10_path) as src:
            dn = src.read(1).astype(np.float32)
            meta = src.meta.copy()

        # DN → Top-of-atmosphere spectral radiance
        radiance = ML * dn + AL
        # Radiance → Brightness temperature (Kelvin)
        temp_k = K2 / np.log(K1 / radiance + 1)
        # Replace invalid pixels
        temp_k = np.where(dn == 0, np.nan, temp_k)

        meta.update(dtype="float32", count=1)
        if output_path is None:
            output_path = b10_path.parent / f"{b10_path.stem}_Kelvin.TIF"

        with rasterio.open(output_path, "w", **meta) as dst:
            dst.write(temp_k, 1)

        logger.info(
            f"✅ Thermal band saved: {output_path}\n"
            f"   T range: {np.nanmin(temp_k):.1f}K – {np.nanmax(temp_k):.1f}K"
        )
        return Path(output_path), temp_k

    def detect_heat_anomalies(
        self,
        temp_k: "np.ndarray",
        low_k: float = 305.0,
        high_k: float = 325.0,
    ) -> "np.ndarray":
        """
        Return binary mask of thermal anomalies (potential active dump sites).
        Default range 305-325K excludes normal soil/veg and water.
        """
        return ((temp_k >= low_k) & (temp_k <= high_k)).astype(np.uint8)

    @staticmethod
    def _parse_mtl(mtl_path: Path) -> dict:
        """Parse Landsat MTL metadata for radiometric constants."""
        constants = {}
        with open(mtl_path) as f:
            for line in f:
                for key in (
                    "RADIANCE_MULT_BAND_10",
                    "RADIANCE_ADD_BAND_10",
                    "K1_CONSTANT_BAND_10",
                    "K2_CONSTANT_BAND_10",
                ):
                    if key in line:
                        constants[key] = float(line.split("=")[1].strip())
        return constants


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("LandsatWitness ready. Set USGS_USER and USGS_PASS to begin.")
    print("Run: python -m src.data.landsat_downloader")
