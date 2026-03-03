"""
src/data/real_sentinel_api.py
──────────────────────────────
The Sentinel Archive Hunter & Orbital Extraction Suite.
Direct OData API hunting for real photons over Madurai.
"""

from typing import List, Dict, Optional
import requests
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
import zipfile
import rasterio
import numpy as np
from src.auth.copernicus_auth import ESAOrbitalConnector

class SentinelArchiveHunter:
    """
    OData API interface to real ESA catalog.
    Returns actual product metadata with download URLs.
    """
    
    BASE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1"
    
    def __init__(self, connector: ESAOrbitalConnector):
        self.connector = connector
        
    def hunt_madurai_dumps(self, 
                          zone: str,
                          coords: tuple,  # (lat, lon)
                          radius_m: int = 5000,
                          date_start: Optional[str] = None,
                          date_end: Optional[str] = None,
                          max_cloud: float = 15.0,
                          max_results: int = 50) -> List[Dict]:
        """
        Real query. Real results. Real satellite passes over Madurai.
        """
        lat, lon = coords
        # Rough square buffer
        dlat = radius_m / 111320
        dlon = radius_m / (111320 * np.cos(np.radians(lat)))
        
        footprint = f"POLYGON(({lon-dlon} {lat-dlat}, {lon+dlon} {lat-dlat}, {lon+dlon} {lat+dlat}, {lon-dlon} {lat+dlat}, {lon-dlon} {lat-dlat}))"
        
        filters = [
            f"Collection/Name eq 'SENTINEL-2'",
            f"contains(Name,'S2MSI2A')",  # Level-2A (surface reflectance)
            f"OData.CSC.Intersects(area=geography'SRID=4326;{footprint}')",
            f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value lt {max_cloud})"
        ]
        
        if date_start and date_end:
            filters.append(f"ContentDate/Start gt {date_start}T00:00:00.000Z")
            filters.append(f"ContentDate/Start lt {date_end}T23:59:59.999Z")
        
        filter_query = " and ".join(filters)
        url = f"{self.BASE_URL}/Products?$filter={filter_query}&$top={max_results}&$orderby=ContentDate/Start desc&$expand=Attributes"
        
        response = requests.get(url, headers=self.connector.get_auth_header(), timeout=60)
        response.raise_for_status()
        
        products = response.json().get("value", [])
        return products

class SatelliteDataExtraction:
    """
    Real download and extraction of .SAFE payloads.
    """
    
    def __init__(self, connector: ESAOrbitalConnector, download_root: str = "data/raw"):
        self.connector = connector
        self.download_root = Path(download_root)
        self.download_root.mkdir(parents=True, exist_ok=True)
        
    def extract_to_ground(self, product: Dict) -> Path:
        product_id = product["Id"]
        product_name = product["Name"]
        
        zip_path = self.download_root / f"{product_name}.zip"
        safe_path = self.download_root / f"{product_name}.SAFE"
        
        if safe_path.exists():
            return safe_path
            
        download_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
        
        print(f"⬇️  Downloading orbital payload: {product_name}")
        with requests.get(download_url, headers=self.connector.get_auth_header(), stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            with open(zip_path, 'wb') as f:
                with tqdm(total=total_size, unit='B', unit_scale=True) as pbar:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        print(f"📦 Extracting {product_name}...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.download_root)
        
        zip_path.unlink()
        return safe_path

    def get_band_path(self, safe_path: Path, band: str, resolution: str = "10m") -> Optional[Path]:
        """Finds the path to a specific Sentinel-2 band file."""
        granule_path = list(safe_path.glob("GRANULE/*/IMG_DATA"))[0]
        res_folder = granule_path / f"R{resolution}"
        band_files = list(res_folder.glob(f"*{band}*.jp2"))
        if not band_files:
            band_files = list(granule_path.rglob(f"*{band}*.jp2"))
        return band_files[0] if band_files else None
