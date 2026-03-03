"""
scripts/full_system_test.py
────────────────────────────
End-to-End System Integration Test for shadow-litter.
Flow: Synthetic Data -> Siamese Inference -> Temporal Validation -> API Sync
"""
from __future__ import annotations
import torch
import numpy as np
import geopandas as gpd
from shapely.geometry import box
from pathlib import Path
import logging

from src.models.siamese_unet import ShadowLitterNet
from src.validation.temporal_validator import TemporalValidator
from src.agent.database import DumpArchive

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IntegrationTest")

def run_test():
    logger.info("🚀 Initiating Full System Integration Test...")
    
    # 1. Setup Model (Oracle)
    model = ShadowLitterNet(in_channels=6, num_classes=2, pretrained=False)
    model.eval()
    
    # 2. Simulate 3 temporal scans (The Sentinel)
    # We'll create 3 slightly overlapping detections to test the Temporal Validator
    scans = []
    base_box = box(78.11, 9.92, 78.115, 9.925) # Main area
    
    # Scan A: Initial detection
    scans.append(gpd.GeoDataFrame({'id':[1], 'confidence':[0.92]}, geometry=[base_box], crs="EPSG:4326"))
    
    # Scan B: Persistent detection (slightly shifted)
    scans.append(gpd.GeoDataFrame({'id':[2], 'confidence':[0.88]}, geometry=[box(78.111, 9.921, 78.116, 9.926)], crs="EPSG:4326"))
    
    # Scan C: Transient Noise (should be filtered out by validator)
    scans.append(gpd.GeoDataFrame({'id':[3], 'confidence':[0.95]}, geometry=[box(78.2, 10.0, 78.21, 10.01)], crs="EPSG:4326"))

    # 3. Temporal Validation (The Validator)
    logger.info("🛡️ Running Temporal Validator...")
    validator = TemporalValidator(tolerance_m=50.0)
    persistent_gdf = validator.calibrate(scans[:2]) # Testing persistence of A & B
    
    # 4. Database Sync (The Librarian)
    logger.info("📚 Syncing persistent detections to DumpArchive...")
    db = DumpArchive()
    for _, row in persistent_gdf.iterrows():
        centroid = row.geometry.centroid
        db.log_detection(
            zone="integration_test_zone",
            lat=centroid.y,
            lon=centroid.x,
            confidence=0.9,
            area_sqm=500.0,
            dump_type="validated_persistent",
            ward="TEST"
        )
    
    stats = db.stats()
    logger.info(f"✅ Integration Test Complete. DB Stats: {stats}")
    db.close()

if __name__ == "__main__":
    run_test()
