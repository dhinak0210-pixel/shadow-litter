"""
src/data/landsat_oracle.py
──────────────────────────
LandsatOracle — detection of thermal anomalies (waste fires/decomposition).
Uses Landsat 8/9 Band 10 (TIRS 1, 10.6–11.19 μm).
"""
from __future__ import annotations
import logging, os
from pathlib import Path
import numpy as np
import rasterio

logger = logging.getLogger(__name__)

class LandsatOracle:
    """
    Analyzes Landsat 8/9 thermal imagery to detect heat signatures (T > 305K)
    consistent with landfill fires or concentrated organic decomposition.
    """
    
    # Band 10 thermal conversion constants (Landsat 8/9)
    K1 = 774.89
    K2 = 1321.08
    M_L = 0.0003342   # Radiance multi
    A_L = 0.1         # Radiance add

    def detect_heat_anomalies(self, b10_path: str, threshold_k: float = 305.0) -> np.ndarray:
        """
        Converts raw DN values to Brightness Temperature (Kelvin) and masks anomalies.
        """
        with rasterio.open(b10_path) as src:
            dn = src.read(1).astype(np.float32)
            profile = src.profile

        # 1. DN to Radiance: L = M_L * DN + A_L
        radiance = self.M_L * dn + self.A_L
        
        # 2. Radiance to Kelvin: T = K2 / ln(K1/L + 1)
        # Avoid log(0)
        radiance = np.where(radiance > 0, radiance, 1e-6)
        kelvin = self.K2 / np.log(self.K1 / radiance + 1)
        
        # 3. Mask anomalies (T > 32°C / 305K)
        mask = (kelvin > threshold_k).astype(np.uint8)
        
        logger.info(f"Thermal scan complete. Max temp: {np.max(kelvin):.1f}K | Anomalies: {np.sum(mask)}")
        return mask, kelvin

    def get_fire_risk_score(self, dump_lat: float, dump_lon: float, kelvin_map: np.ndarray, transform) -> float:
        """Calculate local fire risk based on temperature at a specific dump coordinate."""
        py, px = ~transform * (dump_lon, dump_lat)
        py, px = int(py), int(px)
        # 5x5 window
        window = kelvin_map[max(0, py-2):py+3, max(0, px-2):px+3]
        return float(np.mean(window)) if window.size > 0 else 0.0
