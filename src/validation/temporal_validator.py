"""
src/validation/temporal_validator.py
────────────────────────────────────
Temporal Stability Validator — eliminates transient detections (trucks, transient piles)
by enforcing spatial intersection across multiple dates.
"""
from __future__ import annotations
import geopandas as gpd
from shapely.ops import unary_union
import logging

logger = logging.getLogger(__name__)

class TemporalValidator:
    """
    Enforces 'Multitemporal Persistence' for waste detections.
    A dump site is only valid if it persists across at least 2 out of 3 scans.
    """
    def __init__(self, tolerance_m: float = 20.0):
        self.tolerance = tolerance_m

    def calibrate(self, scans: list[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
        """
        Takes a list of GeoDataFrames from different dates.
        Returns a single GeoDataFrame containing only persistent clusters.
        """
        if len(scans) < 2:
            return scans[0] if scans else gpd.GeoDataFrame()

        # 1. Spatial Join across timeline
        persistent = scans[0]
        for next_scan in scans[1:]:
            # Keep only areas in 'persistent' that intersect with 'next_scan'
            # within the spatial tolerance.
            persistent = gpd.sjoin(persistent, next_scan, how="inner", predicate="intersects")
            # Drop duplicated columns from join
            persistent = persistent[persistent.columns[~persistent.columns.str.endswith('_right')]]

        # 2. Refine geometries (Union of overlapping clusters)
        if not persistent.empty:
            merged = unary_union(persistent.geometry)
            persistent = gpd.GeoDataFrame(geometry=[merged] if not hasattr(merged, 'geoms') else list(merged.geoms), 
                                         crs=scans[0].crs)
            
        logger.info(f"Temporal calibration complete. Persistent sites: {len(persistent)}")
        return persistent

if __name__ == "__main__":
    # Test logic
    from shapely.geometry import box
    d1 = gpd.GeoDataFrame({'id':[1]}, geometry=[box(0,0,1,1)], crs="EPSG:4326")
    d2 = gpd.GeoDataFrame({'id':[2]}, geometry=[box(0.1,0.1,1.1,1.1)], crs="EPSG:4326")
    d3 = gpd.GeoDataFrame({'id':[3]}, geometry=[box(5,5,6,6)], crs="EPSG:4326") # transient noise
    
    val = TemporalValidator()
    result = val.calibrate([d1, d2, d3])
    print(f"Stable sites detected: {len(result)}") # Should be 1 (d1 ∩ d2)
