"""
src/data/synthetic_dumps.py
─────────────────────────────
Synthetic corruption engine.
Generates realistic fake dump sites on clean satellite patches for
zero-label bootstrapping of the change detection model.

Three dump archetypes modelled from real Madurai observations:
  1. Construction debris: dark angular patches, high SWIR reflectance
  2. Household waste: irregular diffuse blobs, low NIR, mid-VIS
  3. Leachate pooling: near-water darkening, water-like spectral signature
"""
from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.ndimage import gaussian_filter, label as ndlabel

logger = logging.getLogger(__name__)


class DumpSimulator:
    """
    Synthesizes realistic dump site textures onto clean satellite imagery.
    Uses spectral manipulation grounded in known waste reflectance profiles.
    """

    DUMP_TYPES = ["construction_debris", "household_waste", "leachate_pooling"]

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)

    # ── Public API ─────────────────────────────────────────────────────────────

    def generate_texture_dump(
        self,
        image: np.ndarray,
        num_patches: int = 5,
        dump_type: Optional[str] = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Add synthetic dump textures to a clean (C, H, W) image.

        Args:
            image:       Clean satellite patch, (C, H, W), float32 in [0, 1]
            num_patches: Number of dump blobs to add
            dump_type:   Force a specific type, or None for random

        Returns:
            (corrupted_image, binary_mask)  mask = 1 where dump was added
        """
        result = image.copy()
        mask = np.zeros(image.shape[1:], dtype=np.uint8)

        for _ in range(num_patches):
            dtype = dump_type or self.rng.choice(self.DUMP_TYPES)
            result, mask = self._place_dump(result, mask, dtype)

        return result, mask

    def generate_bboxes(self, mask: np.ndarray) -> list[tuple[int, int, int, int]]:
        """Return bounding boxes (y1, x1, y2, x2) of labeled dump regions."""
        labeled, n = ndlabel(mask)
        boxes = []
        for i in range(1, n + 1):
            ys, xs = np.where(labeled == i)
            if len(ys) > 0:
                boxes.append((ys.min(), xs.min(), ys.max(), xs.max()))
        return boxes

    # ── Dump placement ────────────────────────────────────────────────────────

    def _place_dump(
        self, image: np.ndarray, mask: np.ndarray, dump_type: str
    ) -> tuple[np.ndarray, np.ndarray]:
        C, H, W = image.shape

        if dump_type == "construction_debris":
            return self._construction_debris(image, mask, H, W)
        elif dump_type == "household_waste":
            return self._household_waste(image, mask, H, W)
        elif dump_type == "leachate_pooling":
            return self._leachate_pool(image, mask, H, W)
        else:
            raise ValueError(f"Unknown dump type: {dump_type}")

    def _construction_debris(
        self, image: np.ndarray, mask: np.ndarray, H: int, W: int
    ) -> tuple[np.ndarray, np.ndarray]:
        """Dark angular patches with elevated SWIR reflectance."""
        # Random rectangle
        h = self.rng.integers(20, 80)
        w = self.rng.integers(30, 100)
        y = self.rng.integers(0, H - h)
        x = self.rng.integers(0, W - w)

        # Rotate mask to make it non-rectangular
        patch_mask = np.zeros((H, W), dtype=np.float32)
        patch_mask[y:y + h, x:x + w] = 1.0

        # Add noisy edges (angular, not smooth)
        noise = self.rng.uniform(0, 0.3, (H, W))
        patch_mask = np.clip(patch_mask + noise * patch_mask, 0, 1)
        patch_mask = (patch_mask > 0.5).astype(np.float32)

        result = image.copy()
        for c in range(image.shape[0]):
            if c in (0, 1, 2):    # RGB: darken (concrete/gravel is dark)
                factor = self.rng.uniform(0.3, 0.6)
                result[c] = result[c] * (1 - patch_mask) + (result[c] * factor) * patch_mask
            elif c == 3:          # NIR: slight drop (no vegetation)
                factor = self.rng.uniform(0.2, 0.5)
                result[c] = result[c] * (1 - patch_mask) + (result[c] * factor) * patch_mask
            elif c in (4, 5):    # SWIR: elevated (mineral exposure)
                factor = self.rng.uniform(1.2, 1.8)
                result[c] = np.clip(result[c] * (1 - patch_mask) + (result[c] * factor) * patch_mask, 0, 1)

        mask = np.clip(mask + patch_mask.astype(np.uint8), 0, 1)
        return result, mask

    def _household_waste(
        self, image: np.ndarray, mask: np.ndarray, H: int, W: int
    ) -> tuple[np.ndarray, np.ndarray]:
        """Irregular diffuse blobs — low NIR, mixed visible reflectance."""
        # Organic blob shape via Gaussian
        cy = self.rng.integers(30, H - 30)
        cx = self.rng.integers(30, W - 30)
        sigma_y = self.rng.uniform(10, 40)
        sigma_x = self.rng.uniform(15, 60)

        yy, xx = np.mgrid[:H, :W]
        blob = np.exp(-((yy - cy) ** 2 / (2 * sigma_y ** 2) +
                        (xx - cx) ** 2 / (2 * sigma_x ** 2)))
        blob = (blob > self.rng.uniform(0.15, 0.5)).astype(np.float32)

        # Smooth edges
        blob = gaussian_filter(blob, sigma=2)
        blob = (blob > 0.3).astype(np.float32)

        result = image.copy()
        for c in range(image.shape[0]):
            if c == 3:   # NIR: strong drop (waste not vegetated)
                target = self.rng.uniform(0.05, 0.15)
                result[c] = result[c] * (1 - blob) + target * blob
            elif c in (0, 1, 2):  # RGB: brightened irregularly
                brightness = self.rng.uniform(0.4, 0.7)
                noise = self.rng.uniform(0.9, 1.1, (H, W))
                result[c] = result[c] * (1 - blob) + (brightness * noise) * blob
                result[c] = np.clip(result[c], 0, 1)

        mask = np.clip(mask + blob.astype(np.uint8), 0, 1)
        return result, mask

    def _leachate_pool(
        self, image: np.ndarray, mask: np.ndarray, H: int, W: int
    ) -> tuple[np.ndarray, np.ndarray]:
        """Near-water darkening — all bands suppressed, especially NIR."""
        cy = self.rng.integers(40, H - 40)
        cx = self.rng.integers(40, W - 40)
        r = self.rng.integers(15, 50)

        yy, xx = np.mgrid[:H, :W]
        circle = ((yy - cy) ** 2 + (xx - cx) ** 2 < r ** 2).astype(np.float32)
        circle = gaussian_filter(circle, sigma=3)
        circle = (circle > 0.5).astype(np.float32)

        result = image.copy()
        target = self.rng.uniform(0.02, 0.08)  # very dark
        for c in range(image.shape[0]):
            result[c] = result[c] * (1 - circle) + target * circle

        mask = np.clip(mask + circle.astype(np.uint8), 0, 1)
        return result, mask


# ── Dataset generation ────────────────────────────────────────────────────────

def create_synthetic_dataset(
    clean_patch_dir: str,
    output_dir: str,
    n_samples: int = 1000,
    positive_fraction: float = 0.50,
    seed: int = 42,
) -> dict:
    """
    Build a synthetic training dataset from clean patches.

    Args:
        clean_patch_dir:   Directory containing .npy clean patches
        output_dir:        Where to write (image.npy, mask.npy, label.json) triplets
        n_samples:         Total samples to generate
        positive_fraction: Fraction that will have synthetic dumps
        seed:              Random seed

    Returns:
        Dict with dataset statistics
    """
    clean_dir = Path(clean_patch_dir)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    patches = sorted(clean_dir.glob("*.npy"))
    if not patches:
        raise FileNotFoundError(f"No .npy patches found in {clean_dir}")

    simulator = DumpSimulator(seed=seed)
    rng = np.random.default_rng(seed)

    stats = {"total": 0, "positive": 0, "negative": 0}

    for i in range(n_samples):
        # Sample a random clean patch
        patch_path = rng.choice(patches)
        clean = np.load(patch_path).astype(np.float32)

        # Normalize to [0, 1] if not already
        if clean.max() > 1.0:
            clean = clean / 10000.0  # Sentinel-2 DN scale
        clean = np.clip(clean, 0, 1)

        is_positive = rng.random() < positive_fraction
        if is_positive:
            n_dumps = rng.integers(1, 5)
            image, mask = simulator.generate_texture_dump(clean, num_patches=int(n_dumps))
            label = 1
            stats["positive"] += 1
        else:
            image = clean
            mask = np.zeros(clean.shape[1:], dtype=np.uint8)
            label = 0
            stats["negative"] += 1

        # Save triplet
        prefix = out_dir / f"sample_{i:06d}"
        np.save(f"{prefix}_image.npy", image.astype(np.float32))
        np.save(f"{prefix}_mask.npy", mask.astype(np.uint8))
        with open(f"{prefix}_label.json", "w") as f:
            import json
            json.dump({"label": label, "source_patch": str(patch_path)}, f)

        stats["total"] += 1
        if (i + 1) % 100 == 0:
            logger.info(f"  Generated {i+1}/{n_samples} samples …")

    logger.info(
        f"✅ Dataset complete: {stats['positive']} positive, "
        f"{stats['negative']} negative → {out_dir}"
    )
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys
    if len(sys.argv) < 3:
        print("Usage: python -m src.data.synthetic_dumps <clean_patches_dir> <output_dir> [n_samples]")
        sys.exit(1)
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
    stats = create_synthetic_dataset(sys.argv[1], sys.argv[2], n_samples=n)
    print(stats)
