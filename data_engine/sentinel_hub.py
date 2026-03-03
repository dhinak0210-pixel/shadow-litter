import os
from datetime import datetime, timedelta
from typing import List, Tuple, Dict
import numpy as np
import rasterio
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
import planetary_computer
import pystac_client

class SentinelFeed:
    """
    Autonomous satellite data acquisition for Madurai region.
    Uses both Copernicus Open Access Hub and Microsoft Planetary Computer.
    """
    
    def __init__(self):
        # Free tier: Planetary Computer (no auth required for search)
        self.catalog = pystac_client.Client.open(
            "https://planetarycomputer.microsoft.com/api/stac/v1",
            modifier=planetary_computer.sign_inplace,
        )
        # Madurai City Bounding Box: [78.0156, 9.8245, 78.2030, 9.9934]
        # Vaigai Riverbed Corridor corridor: [78.0900, 9.8970, 78.1560, 9.9540]
        self.madurai_bbox = [78.0900, 9.8970, 78.1560, 9.9540]
        self.area_of_interest = {
            "type": "Polygon",
            "coordinates": [[
                [78.0900, 9.8970], [78.1560, 9.8970],
                [78.1560, 9.9540], [78.0900, 9.9540],
                [78.0900, 9.8970]
            ]]
        }
        
    def search_temporal_stack(self, 
                            start_date: str, 
                            end_date: str,
                            cloud_cover: float = 20.0) -> List[Dict]:
        """
        Acquire multi-temporal imagery stack for change detection.
        Returns metadata for scenes meeting quality criteria.
        """
        search = self.catalog.search(
            collections=["sentinel-2-l2a"],
            intersects=self.area_of_interest,
            datetime=f"{start_date}/{end_date}",
            query={"eo:cloud_cover": {"lt": cloud_cover}}
        )
        
        items = list(search.get_items())
        
        # Sort by datetime, group by relative orbit for consistency
        scenes = []
        for item in items:
            scenes.append({
                'id': item.id,
                'datetime': item.datetime.isoformat(),
                'cloud_cover': item.properties['eo:cloud_cover'],
                'assets': {k: v.href for k, v in item.assets.items()},
                'bbox': item.bbox,
                'links': item.links
            })
            
        return sorted(scenes, key=lambda x: x['datetime'])
    
    def download_bands(self, scene: Dict, bands: List[str]) -> np.ndarray:
        """
        Download specific spectral bands (B4=Red, B8=NIR, B11=SWIR).
        Returns stacked array [bands, height, width].
        """
        # Use planetary computer signed URLs
        band_urls = {b: scene['assets'][b] for b in bands if b in scene['assets']}
        
        arrays = []
        for band in bands:
            with rasterio.open(band_urls[band]) as src:
                # Read at 10m resolution (resampling if needed)
                data = src.read(1, out_shape=(1098, 1098), resampling=rasterio.enums.Resampling.bilinear)
                arrays.append(data)
                
        return np.stack(arrays)  # Shape: [bands, 1098, 1098]
