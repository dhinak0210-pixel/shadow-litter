"""
src/satellite/live_esa_connection.py
──────────────────────────────────────
PRODUCTION connection to ESA Copernicus Data Space.
Real credentials. Real data. Real time.
"""

import os
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from dataclasses import dataclass
from pathlib import Path
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("esa_connector")

def get_required_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if not value:
        raise RuntimeError(f"Required environment variable {var_name} not set.")
    return value

@dataclass
class LiveESACredentials:
    """Your actual ESA credentials."""
    username: str = get_required_env("COPERNICUS_USER")
    password: str = get_required_env("COPERNICUS_PASS")
    client_id: str = "cdse-public"
    token_url: str = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    
    def __post_init__(self):
        if '@' not in self.username:
            raise ValueError("COPERNICUS_USER must be a valid email")

class LiveSatelliteConnector:
    """
    LIVE connection to ESA's orbital constellation.
    Downloads real photons from space.
    """
    
    BASE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1"
    
    def __init__(self):
        self.creds = LiveESACredentials()
        self._token: Optional[str] = None
        self._expires: Optional[datetime] = None
        
    async def authenticate(self) -> str:
        """Get live OAuth2 token from ESA."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.creds.token_url,
                data={
                    "grant_type": "password",
                    "client_id": self.creds.client_id,
                    "username": self.creds.username,
                    "password": self.creds.password
                },
                timeout=30
            ) as response:
                response.raise_for_status()
                data = await response.json()
                self._token = data["access_token"]
                self._expires = datetime.now() + timedelta(seconds=data["expires_in"])
                
                logger.info("🔑 LIVE ESA authentication successful")
                return self._token
    
    async def get_token(self) -> str:
        """Auto-refresh token."""
        if not self._token or datetime.now() >= self._expires:
            return await self.authenticate()
        return self._token
    
    async def query_live_scenes(self,
                         lat: float,
                         lon: float,
                         radius_m: int = 5000,
                         start_date: str = None,
                         end_date: str = None,
                         max_cloud: float = 15.0) -> List[Dict]:
        """Query REAL satellite catalog for ACTUAL scenes."""
        from shapely.geometry import Point
        token = await self.get_token()
        
        point = Point(lon, lat)
        bbox = point.buffer(radius_m / 111320)
        footprint = bbox.envelope.wkt
        
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        filters = [
            f"Collection/Name eq 'SENTINEL-2'",
            f"contains(Name,'S2MSI2A')",
            f"OData.CSC.Intersects(area=geography'SRID=4326;{footprint}')",
            f"ContentDate/Start gt {start_date}T00:00:00.000Z",
            f"ContentDate/Start lt {end_date}T23:59:59.999Z",
            f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value lt {max_cloud})"
        ]
        
        url = f"{self.BASE_URL}/Products?$filter={' and '.join(filters)}&$top=20&$orderby=ContentDate/Start desc"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=60
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("value", [])

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError, IOError)),
        before_sleep=lambda retry_state: logger.warning(f"Download failed, retrying: {retry_state.outcome.exception()}")
    )
    async def download_live_product(self, product_id: str, product_name: str, output_dir: str = "./data/live_downloads") -> str:
        """Download REAL satellite product from ESA servers with resume support."""
        import zipfile
        token = await self.get_token()
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        download_url = f"{self.BASE_URL}/Products({product_id})/$value"
        output_path = output_dir / f"{product_name}.zip"
        temp_path = output_path.with_suffix('.zip.tmp')
        
        resume_byte = temp_path.stat().st_size if temp_path.exists() else 0
        headers = {"Authorization": f"Bearer {token}"}
        if resume_byte > 0:
            headers["Range"] = f"bytes={resume_byte}-"
            
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url, headers=headers, timeout=None) as response:
                response.raise_for_status()
                
                expected_size = int(response.headers.get('content-length', 0)) + resume_byte
                if expected_size < 100_000_000 and resume_byte == 0:
                    logger.warning(f"Suspicious file size: {expected_size}")
                
                mode = 'ab' if resume_byte > 0 else 'wb'
                with open(temp_path, mode) as f:
                    async for chunk in response.content.iter_chunked(8192):
                        if chunk:
                            f.write(chunk)
                
                if temp_path.stat().st_size != expected_size:
                    raise IOError(f"Size mismatch: got {temp_path.stat().st_size}, expected {expected_size}")
                
                temp_path.rename(output_path)
        
        safe_path = output_dir / f"{product_name}.SAFE"
        # Run extraction in a thread to not block the event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_extract, output_path, safe_path)
        
        os.remove(output_path)
        return str(safe_path)

    def _sync_extract(self, zip_path, extract_path):
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
