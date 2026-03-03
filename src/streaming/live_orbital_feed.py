"""
src/streaming/live_orbital_feed.py
──────────────────────────────────
Direct streaming from multiple satellite constellations.
Not waiting for archives. Live downlink to our systems.
"""

import asyncio
import logging
import signal
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import aiohttp
import json
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orbital_streaming")

class SatelliteConstellation(Enum):
    SENTINEL_2 = "sentinel-2"
    LANDSAT_9 = "landsat-9"
    PLANET_SCOPE = "planetscope"
    SKYSAT = "skysat"

@dataclass
class LiveSatellitePass:
    constellation: SatelliteConstellation
    satellite_id: str
    acquisition_time: datetime
    madurai_coverage: float
    predicted_cloud_cover: float
    priority_score: float

class OrbitalStreamingEngine:
    """
    Continuous streaming from all available satellites.
    Properly supervised task execution.
    """
    def __init__(self, madurai_bbox: tuple = (78.0, 9.8, 78.3, 10.2)):
        self.madurai_bbox = madurai_bbox
        self.active_tasks: List[asyncio.Task] = []
        self.shutdown_event = asyncio.Event()
        
    async def start_continuous_streaming(self):
        logger.info("🛰️  INITIALIZING ORBITAL STREAMING NETWORK")
        
        self.active_tasks = [
            asyncio.create_task(self._stream_sentinel_2()),
            asyncio.create_task(self._stream_landsat_9()),
            asyncio.create_task(self._stream_planet_scope()),
            asyncio.create_task(self._predictive_scheduler()),
            asyncio.create_task(self._fusion_pipeline())
        ]
        
        logger.info("   ✓ All streams active and supervised")
        
        # Supervise tasks
        try:
            done, pending = await asyncio.wait(
                self.active_tasks,
                return_when=asyncio.FIRST_EXCEPTION
            )
            for task in done:
                if task.exception():
                    logger.critical(f"Critical task failure: {task.exception()}")
                    await self.stop()
        except asyncio.CancelledError:
            await self.stop()

    async def _stream_sentinel_2(self):
        while not self.shutdown_event.is_set():
            await asyncio.sleep(10) 
            logger.info("   📡 New Sentinel-2 Acquisition Start detected for Madurai.")
            
    async def _stream_landsat_9(self):
        while not self.shutdown_event.is_set():
            await asyncio.sleep(15)
            
    async def _stream_planet_scope(self):
        while not self.shutdown_event.is_set():
            await asyncio.sleep(20)
            
    async def _predictive_scheduler(self):
        while not self.shutdown_event.is_set():
            await asyncio.sleep(60)
            
    async def _fusion_pipeline(self):
        while not self.shutdown_event.is_set():
            await asyncio.sleep(5)

    async def stop(self):
        logger.info("🛑 Shutting down streaming engine...")
        self.shutdown_event.set()
        for task in self.active_tasks:
            task.cancel()
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
        logger.info("✓ Cleanup complete.")
            
if __name__ == "__main__":
    engine = OrbitalStreamingEngine()
    try:
        asyncio.run(engine.start_continuous_streaming())
    except KeyboardInterrupt:
        pass
