"""
src/data/coregistration.py
───────────────────────────
Coregistration spell — sub-pixel alignment of multi-temporal satellite imagery
using phase correlation on NIR bands. Essential for change detection:
unaligned images produce false change signals.

Method: OpenCV phase correlation (FFT-based)
Reference: Always register all images to the oldest in-zone image.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import rasterio
from rasterio.transform import Affine

logger = logging.getLogger(__name__)

# Band index for NIR (B08) in our standard 6-band stack (0-indexed)
NIR_BAND_IDX = 3   # B02=0, B03=1, B04=2, B08=3, B11=4, B12=5


def align_images(
    reference_path: str,
    target_path: str,
    output_path: Optional[str] = None,
    nir_band_idx: int = NIR_BAND_IDX,
    upsample_factor: int = 100,
) -> tuple[Path, np.ndarray]:
    """
    Align target image to reference using phase correlation on NIR band.

    Args:
        reference_path:   Path to reference (earlier date) GeoTIFF
        target_path:      Path to target (later date) GeoTIFF to align
        output_path:      Where to save the aligned GeoTIFF (auto-named if None)
        nir_band_idx:     0-indexed band index of NIR channel
        upsample_factor:  Sub-pixel precision (100 = 0.01px)

    Returns:
        (aligned_path, shift_vector [dy, dx])
    """
    ref_path = Path(reference_path)
    tgt_path = Path(target_path)

    with rasterio.open(ref_path) as ref_src:
        ref_nir = ref_src.read(nir_band_idx + 1).astype(np.float32)
        ref_meta = ref_src.meta.copy()
        ref_transform = ref_src.transform

    with rasterio.open(tgt_path) as tgt_src:
        tgt_all = tgt_src.read().astype(np.float32)   # (C, H, W)
        tgt_nir = tgt_all[nir_band_idx]

    # Ensure same shape (resize target to reference if needed)
    H, W = ref_nir.shape
    if tgt_nir.shape != (H, W):
        tgt_nir = cv2.resize(tgt_nir, (W, H), interpolation=cv2.INTER_LINEAR)
        resized_all = np.stack([
            cv2.resize(tgt_all[c], (W, H), interpolation=cv2.INTER_LINEAR)
            for c in range(tgt_all.shape[0])
        ])
        tgt_all = resized_all

    # Phase correlation for shift estimation
    ref_norm = _normalize_band(ref_nir)
    tgt_norm = _normalize_band(tgt_nir)

    shift, _ = cv2.phaseCorrelate(ref_norm, tgt_norm)   # (dx, dy)
    dx, dy = shift
    logger.info(f"Shift: dx={dx:.3f}px, dy={dy:.3f}px")

    # Apply translation warp to all bands
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    aligned_bands = np.stack([
        cv2.warpAffine(
            tgt_all[c], M, (W, H),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT_101,
        )
        for c in range(tgt_all.shape[0])
    ])

    # Adjust transform to reflect sub-pixel shift
    new_transform = Affine(
        ref_transform.a, ref_transform.b, ref_transform.c + dx * ref_transform.a,
        ref_transform.d, ref_transform.e, ref_transform.f + dy * ref_transform.e,
    )
    ref_meta.update(transform=new_transform)

    # Save
    if output_path is None:
        output_path = tgt_path.parent / f"{tgt_path.stem}_coreg.tif"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(output_path, "w", **ref_meta) as dst:
        dst.write(aligned_bands)

    logger.info(f"✅ Aligned image saved → {output_path}")
    return output_path, np.array([dy, dx])


def _normalize_band(arr: np.ndarray) -> np.ndarray:
    """Normalize array to [0, 1] float32 for phase correlation."""
    p2, p98 = np.percentile(arr, 2), np.percentile(arr, 98)
    arr = np.clip(arr, p2, p98)
    arr = (arr - p2) / (p98 - p2 + 1e-8)
    return arr.astype(np.float32)


def compute_alignment_score(
    reference_path: str,
    aligned_path: str,
    nir_band_idx: int = NIR_BAND_IDX,
) -> float:
    """
    Compute normalized cross-correlation score between reference and aligned image.
    Score 1.0 = perfect alignment, 0.0 = completely decorrelated.
    """
    with rasterio.open(reference_path) as src:
        ref = _normalize_band(src.read(nir_band_idx + 1).astype(np.float32))
    with rasterio.open(aligned_path) as src:
        aln = _normalize_band(src.read(nir_band_idx + 1).astype(np.float32))

    numerator = np.sum(ref * aln)
    denominator = np.sqrt(np.sum(ref ** 2) * np.sum(aln ** 2))
    score = numerator / (denominator + 1e-8)
    logger.info(f"Alignment NCC score: {score:.4f}")
    return float(score)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 3:
        print("Usage: python -m src.data.coregistration <reference.tif> <target.tif>")
        sys.exit(1)
    path, shift = align_images(sys.argv[1], sys.argv[2])
    print(f"Aligned: {path}")
    print(f"Shift:   dy={shift[0]:.3f}  dx={shift[1]:.3f} pixels")
