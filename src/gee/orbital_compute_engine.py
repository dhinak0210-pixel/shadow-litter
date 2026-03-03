"""
src/gee/orbital_compute_engine.py
──────────────────────────────────
Google Earth Engine Protocol for server-side waste detection.
Processing petabytes in the cloud — zero-download workflow.
"""

import ee
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class OrbitalComputeEngine:
    def __init__(self, project_id: str):
        self.project_id = project_id
        try:
            ee.Initialize(project=project_id)
            print(f"🌍 Connected to GEE project: {project_id}")
        except Exception as e:
            print(f"⚠️ GEE Initialization failed: {e}. Run 'earthengine authenticate'.")

    def build_sentinel_collection(self,
                                   roi: ee.Geometry,
                                   start_date: str,
                                   end_date: str,
                                   cloud_threshold: float = 10.0) -> ee.ImageCollection:
        """Assembles a cloud-free Sentinel-2 collection for a region."""
        return (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(roi)
                .filterDate(start_date, end_date)
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_threshold))
                .map(self._preprocess)
                .select(["B2", "B3", "B4", "B8", "SCL"]))

    def _preprocess(self, image: ee.Image) -> ee.Image:
        """Quality masking and spectral scaling."""
        scl = image.select("SCL")
        # Keep only clear pixels (Vegetation, Soil, Water, Low/Med Cloud Prob)
        mask = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).Or(scl.eq(7))
        return image.divide(10000).updateMask(mask).copyProperties(image, ["system:time_start"])

    def detect_changes(self, t1: ee.Image, t2: ee.Image) -> ee.Image:
        """Spectral change detection (Server-side)."""
        ndvi1 = t1.normalizedDifference(['B8', 'B4'])
        ndvi2 = t2.normalizedDifference(['B8', 'B4'])
        
        # Detect decrease in vegetation or surge in bright reflectance
        diff = ndvi1.subtract(ndvi2).abs()
        return diff.gt(0.3).selfMask()

    def export_results(self, image: ee.Image, name: str, bucket: str, region: ee.Geometry):
        """Triggers a GEE Export task to Google Cloud Storage."""
        task = ee.batch.Export.image.toCloudStorage(
            image=image,
            description=name,
            bucket=bucket,
            fileNamePrefix=f"detections/{name}",
            region=region,
            scale=10,
            fileFormat='GeoTIFF'
        )
        task.start()
        print(f"☁️  Export task started: {name} (ID: {task.id})")
        return task.id
