"""
LIVE connection to AWS Earth Search STAC API for Sentinel-2.
Real open data. No credentials required.
"""
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List
import logging

logger = logging.getLogger("stac_connector")

class LiveSatelliteConnector:
    """
    Connector for Earth Search v1 (AWS Open Data).
    Bypasses ESA authentication while still providing real Sentinel-2 data.
    """
    BASE_URL = "https://earth-search.aws.element84.com/v1"

    async def query_live_scenes(self,
                         lat: float,
                         lon: float,
                         radius_m: int = 5000,
                         start_date: str = None,
                         end_date: str = None,
                         max_cloud: float = 15.0) -> List[Dict]:
        """Query REAL satellite catalog from AWS Open Data."""
        logger.info("📡 Establishing unauthenticated link to Earth Search (AWS Sentinel-2 L2A)")
        
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

        # Approx 1 degree = 111.32km
        offset = radius_m / 111320.0
        bbox = [lon - offset, lat - offset, lon + offset, lat + offset]

        payload = {
            "collections": ["sentinel-2-l2a"],
            "bbox": bbox,
            "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
            "query": {
                "eo:cloud_cover": {"lt": max_cloud}
            },
            "limit": 20
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.BASE_URL}/search", json=payload, timeout=30) as response:
                response.raise_for_status()
                data = await response.json()
                features = data.get("features", [])
                
                # Transform STAC format to our unified schema
                mapped_scenes = []
                for f in features:
                    mapped_scenes.append({
                        "Name": f["id"],
                        "ContentDate": {
                            "Start": f["properties"]["datetime"]
                        },
                        "Attributes": [{"Value": f["properties"].get("eo:cloud_cover", 0)}]
                    })
                
                # Sort by date (newest first)
                sorted_scenes = sorted(mapped_scenes, key=lambda x: x["ContentDate"]["Start"], reverse=True)
                return sorted_scenes

    async def download_live_product(self, product_id: str, product_name: str, output_dir: str = "./data/live_downloads") -> str:
        """Download logic stub for AWS data (which natively supports Cloud Optimized GeoTIFFs without zip downloads)."""
        logger.info(f"Accessing COG stream for {product_name}")
        return f"s3://sentinel-s2-l2a/cogs/{product_name}"
