"""
Google Earth Engine — petabytes of satellite history.
Required: Google Cloud project with Earth Engine API enabled.
"""

import ee
import os
from typing import List, Dict
import json
from typing import Optional

class GEEDataEngine:
    """
    Direct GEE Python API access. No downloading. Server-side processing.
    For when local storage is impossible.
    """
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.initialized = False
        
    def initialize(self, service_account_key: Optional[str] = None):
        """Authenticate to GEE."""
        if service_account_key:
            # Service account for production
            credentials = ee.ServiceAccountCredentials(
                None,  # Email extracted from key
                service_account_key
            )
            ee.Initialize(credentials, project=self.project_id)
        else:
            # User authentication (development)
            ee.Initialize(project=self.project_id)
        self.initialized = True
        
    def get_sentinel2_collection(self, region: ee.Geometry, 
                                  date_start: str, 
                                  date_end: str,
                                  cloud_cover_max: float = 20.0) -> ee.ImageCollection:
        """
        Real Sentinel-2 L2A collection, server-side filtered.
        Returns: ImageCollection ready for analysis.
        """
        collection = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                     .filterBounds(region)
                     .filterDate(date_start, date_end)
                     .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover_max))
                     .map(self._mask_clouds_s2))
        
        return collection
    
    def _mask_clouds_s2(self, image: ee.Image) -> ee.Image:
        """SCL-based cloud masking. Server-side."""
        scl = image.select("SCL")
        # Keep: vegetation(4), bare soil(5), water(6), low(7), med(8), high(9) proba clouds
        mask = scl.lt(3).Or(scl.gt(7))  # Remove clouds, shadows, cirrus
        return image.updateMask(mask.Not())
    
    def export_to_drive(self, image: ee.Image, 
                       description: str,
                       folder: str,
                       region: ee.Geometry,
                       scale: float = 10.0):
        """Export real processed data to Google Drive."""
        task = ee.batch.Export.image.toDrive(
            image=image,
            description=description,
            folder=folder,
            region=region,
            scale=scale,
            crs="EPSG:4326",
            maxPixels=1e13
        )
        task.start()
        return task.id

# GEE is the secret weapon — process terabytes without downloading.
