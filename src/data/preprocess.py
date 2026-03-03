"""
src/data/preprocess.py
──────────────────────
Atmospheric clarity pipeline:
  1. Read raw Sentinel-2 .SAFE folders
  2. Stack selected bands into a multi-channel GeoTIFF
  3. Normalize reflectance values
  4. Tile into patches of (patch_size × patch_size)
  5. Split into train / val / test
"""
from __future__ import annotations

import logging
import random
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window
import yaml

logger = logging.getLogger(__name__)

BAND_FILENAMES = {
    "B02": "B02_10m.jp2",
    "B03": "B03_10m.jp2",
    "B04": "B04_10m.jp2",
    "B08": "B08_10m.jp2",
    "B11": "B11_20m.jp2",
    "B12": "B12_20m.jp2",
}


def load_config(path: str = "configs/config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def find_band_files(safe_dir: Path, bands: list[str]) -> dict[str, Path]:
    """Locate band JP2 files inside a .SAFE directory."""
    found = {}
    for band in bands:
        fname = BAND_FILENAMES[band]
        matches = list(safe_dir.rglob(f"*{fname}"))
        if matches:
            found[band] = matches[0]
        else:
            logger.warning(f"Band {band} not found in {safe_dir}")
    return found


def stack_bands(band_paths: dict[str, Path], target_shape: tuple[int, int]) -> np.ndarray:
    """Read and stack bands into (C, H, W) array, resizing to target_shape."""
    import skimage.transform as skt
    arrays = []
    for band, path in band_paths.items():
        with rasterio.open(path) as src:
            data = src.read(1).astype(np.float32)
            if data.shape != target_shape:
                data = skt.resize(data, target_shape, anti_aliasing=True)
        arrays.append(data)
    return np.stack(arrays, axis=0)  # (C, H, W)


def normalize(arr: np.ndarray) -> np.ndarray:
    """Scale reflectance to [0, 1] using 2nd–98th percentile clipping."""
    p2, p98 = np.percentile(arr, 2), np.percentile(arr, 98)
    arr = np.clip(arr, p2, p98)
    return (arr - p2) / (p98 - p2 + 1e-8)


def extract_patches(arr: np.ndarray, patch_size: int, overlap: int) -> list[np.ndarray]:
    """Tile (C, H, W) into overlapping patches of (C, patch_size, patch_size)."""
    _, H, W = arr.shape
    stride = patch_size - overlap
    patches = []
    for y in range(0, H - patch_size + 1, stride):
        for x in range(0, W - patch_size + 1, stride):
            patch = arr[:, y:y + patch_size, x:x + patch_size]
            patches.append(patch)
    return patches


def save_patches(patches: list[np.ndarray], out_dir: Path, prefix: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, patch in enumerate(patches):
        np.save(out_dir / f"{prefix}_{i:05d}.npy", patch)


def run_preprocessing(config_path: str = "configs/config.yaml") -> None:
    cfg = load_config(config_path)
    s_cfg = cfg["sentinel"]
    p_cfg = cfg["paths"]
    pre = cfg["preprocessing"]

    raw_dir = Path(p_cfg["raw"])
    proc_dir = Path(p_cfg["processed"])
    splits_dir = Path(p_cfg["splits"])

    safe_dirs = list(raw_dir.glob("*.SAFE"))
    if not safe_dirs:
        logger.error(f"No .SAFE folders found in {raw_dir}. Run download.py first.")
        return

    logger.info(f"Found {len(safe_dirs)} .SAFE products to process …")
    all_patches: list[np.ndarray] = []

    for safe_dir in safe_dirs:
        logger.info(f"Processing {safe_dir.name} …")
        band_paths = find_band_files(safe_dir, s_cfg["bands"])
        if len(band_paths) < len(s_cfg["bands"]):
            logger.warning(f"Skipping {safe_dir.name} — missing bands")
            continue

        # Use B04 (Red) as reference shape
        with rasterio.open(band_paths.get("B04", list(band_paths.values())[0])) as src:
            H, W = src.height, src.width

        arr = stack_bands(band_paths, (H, W))
        if pre["normalize"]:
            arr = normalize(arr)

        patches = extract_patches(arr, pre["patch_size"], pre["overlap"])
        all_patches.extend(patches)
        logger.info(f"  → {len(patches)} patches extracted")

    random.seed(cfg["training"]["seed"])
    random.shuffle(all_patches)

    n = len(all_patches)
    n_train = int(n * pre["train_ratio"])
    n_val = int(n * pre["val_ratio"])

    train_patches = all_patches[:n_train]
    val_patches = all_patches[n_train:n_train + n_val]
    test_patches = all_patches[n_train + n_val:]

    logger.info(f"Split: {len(train_patches)} train / {len(val_patches)} val / {len(test_patches)} test")

    save_patches(train_patches, splits_dir / "train", "patch")
    save_patches(val_patches, splits_dir / "val", "patch")
    save_patches(test_patches, splits_dir / "test", "patch")

    logger.info("✅ Preprocessing complete.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_preprocessing()
