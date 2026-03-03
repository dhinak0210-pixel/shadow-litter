"""
src/data/harmonization.py
──────────────────────────
Harmonization ritual — matches histogram distributions between satellite images.
Essential when combining:
  - Sentinel-2 vs Sentinel-2 (different dates, different sun angles)
  - Sentinel-2 vs Landsat (different sensors, different spectral response)

Method: Cumulative distribution function (CDF) matching, per band.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import rasterio

logger = logging.getLogger(__name__)


def histogram_match(
    source_path: str,
    reference_path: str,
    output_path: Optional[str] = None,
    n_bins: int = 2048,
) -> Path:
    """
    Match the histogram of source to that of reference, per band.

    Args:
        source_path:    GeoTIFF to adjust
        reference_path: GeoTIFF whose histogram is the target
        output_path:    Where to write the harmonized GeoTIFF
        n_bins:         Number of histogram bins (higher = more precise)

    Returns:
        Path to harmonized GeoTIFF
    """
    src_path = Path(source_path)
    ref_path = Path(reference_path)

    with rasterio.open(src_path) as src:
        src_data = src.read().astype(np.float32)   # (C, H, W)
        meta = src.meta.copy()

    with rasterio.open(ref_path) as ref:
        ref_data = ref.read().astype(np.float32)

    n_bands = src_data.shape[0]
    matched = np.zeros_like(src_data)

    for b in range(n_bands):
        matched[b] = _match_band(src_data[b], ref_data[b], n_bins)
        logger.debug(f"Band {b+1}: histogram matched")

    if output_path is None:
        output_path = src_path.parent / f"{src_path.stem}_harmonized.tif"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(output_path, "w", **meta) as dst:
        dst.write(matched)

    logger.info(f"✅ Harmonized image saved → {output_path}")
    return output_path


def _match_band(source: np.ndarray, reference: np.ndarray, n_bins: int) -> np.ndarray:
    """CDF matching for a single 2D band array."""
    src_flat = source.ravel()
    ref_flat = reference.ravel()

    # Remove NaN/zero (no-data) pixels from reference distribution
    ref_valid = ref_flat[np.isfinite(ref_flat) & (ref_flat > 0)]
    src_valid_mask = np.isfinite(src_flat) & (src_flat > 0)

    if len(ref_valid) == 0 or src_valid_mask.sum() == 0:
        return source  # nothing to match

    # Compute CDFs
    src_hist, src_bins = np.histogram(src_flat[src_valid_mask], bins=n_bins, density=True)
    ref_hist, ref_bins = np.histogram(ref_valid, bins=n_bins, density=True)

    src_cdf = np.cumsum(src_hist) / src_hist.sum()
    ref_cdf = np.cumsum(ref_hist) / ref_hist.sum()

    # Build lookup: for each src value, find matching ref value
    src_midpoints = (src_bins[:-1] + src_bins[1:]) / 2
    ref_midpoints = (ref_bins[:-1] + ref_bins[1:]) / 2

    matched_flat = np.interp(
        np.interp(src_flat, src_midpoints, src_cdf),
        ref_cdf,
        ref_midpoints,
    )
    # Preserve no-data pixels
    matched_flat[~src_valid_mask] = source.ravel()[~src_valid_mask]
    return matched_flat.reshape(source.shape)


def sentinel_to_landsat_normalize(
    sentinel_path: str,
    output_path: Optional[str] = None,
) -> Path:
    """
    Approximate normalization of Sentinel-2 reflectance to Landsat OLI range.
    Uses band-pair regression coefficients from published harmonization studies.
    (Roy et al. 2016 coefficients for overlapping bands)
    """
    # Approximate linear coefficients: sentinel → landsat (slope, intercept)
    COEFFICIENTS = {
        0: (0.9778, 0.0053),   # B02 → B2  (Blue)
        1: (1.0040, -0.0026),  # B03 → B3  (Green)
        2: (0.9528, 0.0148),   # B04 → B4  (Red)
        3: (0.8921, 0.0029),   # B08 → B5  (NIR)
    }

    src_path = Path(sentinel_path)
    with rasterio.open(src_path) as src:
        data = src.read().astype(np.float32)
        meta = src.meta.copy()

    for b_idx, (slope, intercept) in COEFFICIENTS.items():
        if b_idx < data.shape[0]:
            data[b_idx] = data[b_idx] * slope + intercept

    if output_path is None:
        output_path = src_path.parent / f"{src_path.stem}_ls_norm.tif"
    output_path = Path(output_path)
    with rasterio.open(output_path, "w", **meta) as dst:
        dst.write(data)

    logger.info(f"✅ Landsat-normalized Sentinel-2 → {output_path}")
    return output_path
