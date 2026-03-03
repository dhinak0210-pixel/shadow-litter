"""
src/data/patchify.py
─────────────────────
Patch extraction ritual.
Tiles large satellite GeoTIFFs into 256×256 overlapping patches.
Each patch saved as .npy with a companion JSON metadata file.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Generator, Optional

import numpy as np
import rasterio
from rasterio.transform import Affine

logger = logging.getLogger(__name__)


def extract_patches(
    image_path: str,
    patch_size: int = 256,
    stride: int = 128,
    output_dir: Optional[str] = None,
    min_valid_fraction: float = 0.80,
) -> list[dict]:
    """
    Tile a GeoTIFF into overlapping patches.

    Args:
        image_path:          Path to multi-band GeoTIFF
        patch_size:          Patch height and width in pixels
        stride:              Pixels between patch starts (overlap = patch_size - stride)
        output_dir:          Where to save patches (auto-named if None)
        min_valid_fraction:  Skip patches with too many zero/NaN pixels

    Returns:
        List of patch metadata dicts
    """
    img_path = Path(image_path)
    if output_dir is None:
        output_dir = img_path.parent / img_path.stem / "patches"
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata_list = []

    with rasterio.open(img_path) as src:
        data = src.read().astype(np.float32)   # (C, H, W)
        transform = src.transform
        crs = str(src.crs)
        _, H, W = data.shape

    patch_count = 0
    for y, x, patch in _sliding_window(data, patch_size, stride):
        # Quality filter: skip if too many invalid pixels
        valid = np.isfinite(patch) & (patch != 0)
        if valid.mean() < min_valid_fraction:
            continue

        # Compute geo-coordinates of patch center
        center_x = x + patch_size // 2
        center_y = y + patch_size // 2
        lon, lat = transform * (center_x, center_y)

        fname = f"patch_{patch_count:06d}_y{y:04d}x{x:04d}"
        np.save(out_dir / f"{fname}.npy", patch)

        meta = {
            "file": str(out_dir / f"{fname}.npy"),
            "source_image": str(img_path),
            "pixel_y": y,
            "pixel_x": x,
            "patch_size": patch_size,
            "stride": stride,
            "center_lat": round(lat, 6),
            "center_lon": round(lon, 6),
            "crs": crs,
        }
        metadata_list.append(meta)
        patch_count += 1

    # Write metadata index
    meta_path = out_dir / "patches_index.json"
    with open(meta_path, "w") as f:
        json.dump(metadata_list, f, indent=2)

    logger.info(
        f"✅ {patch_count} patches extracted from {img_path.name} → {out_dir}"
    )
    return metadata_list


def _sliding_window(
    arr: np.ndarray,
    patch_size: int,
    stride: int,
) -> Generator[tuple[int, int, np.ndarray], None, None]:
    """Yield (y, x, patch) for all valid windows."""
    _, H, W = arr.shape
    for y in range(0, H - patch_size + 1, stride):
        for x in range(0, W - patch_size + 1, stride):
            yield y, x, arr[:, y:y + patch_size, x:x + patch_size]


def load_patch(patch_path: str) -> np.ndarray:
    """Load a single patch from .npy file."""
    return np.load(patch_path).astype(np.float32)


def load_patch_index(output_dir: str) -> list[dict]:
    """Load the patches_index.json from a patch directory."""
    index_path = Path(output_dir) / "patches_index.json"
    if not index_path.exists():
        raise FileNotFoundError(f"No patch index at {index_path}")
    with open(index_path) as f:
        return json.load(f)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        print("Usage: python -m src.data.patchify <image.tif> [patch_size] [stride]")
        sys.exit(1)
    ps = int(sys.argv[2]) if len(sys.argv) > 2 else 256
    st = int(sys.argv[3]) if len(sys.argv) > 3 else 128
    patches = extract_patches(sys.argv[1], patch_size=ps, stride=st)
    print(f"Extracted {len(patches)} patches.")
