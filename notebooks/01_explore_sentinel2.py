"""
notebooks/01_explore_sentinel2.py
──────────────────────────────────
Exploratory spell: visualise a Sentinel-2 tile, check band statistics,
and preview what the model will see.
Run as a plain Python script or open in VS Code as a Jupyter notebook
(requires jupyter / jupytext).
"""

# %% [markdown]
# # 🛰️ Sentinel-2 Exploratory Analysis — Madurai AOI

# %% imports
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import rasterio

# %% config
# Edit this to point at a real .SAFE directory after downloading
SAMPLE_SAFE = Path("data/raw")
OUTPUT_DIR  = Path("notebooks/outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# %% load a sample band
# Looks for the first B04 (Red) band in any .SAFE folder
safe_dirs = list(SAMPLE_SAFE.glob("*.SAFE"))
if not safe_dirs:
    print("⚠️  No .SAFE directories found. Run python -m src.data.download first.")
else:
    safe = safe_dirs[0]
    red_file = next(safe.rglob("*B04_10m.jp2"), None)
    nir_file = next(safe.rglob("*B08_10m.jp2"), None)

    if red_file and nir_file:
        with rasterio.open(red_file) as src:
            red = src.read(1).astype(np.float32)
        with rasterio.open(nir_file) as src:
            nir = src.read(1).astype(np.float32)

        # NDVI — proxy for vegetation vs. bare soil / waste
        ndvi = (nir - red) / (nir + red + 1e-8)

        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        axes[0].imshow(red,  cmap="Reds",    vmin=np.percentile(red, 2),  vmax=np.percentile(red, 98))
        axes[0].set_title("Red Band (B04)")
        axes[1].imshow(nir,  cmap="Greens",  vmin=np.percentile(nir, 2),  vmax=np.percentile(nir, 98))
        axes[1].set_title("NIR Band (B08)")
        axes[2].imshow(ndvi, cmap="RdYlGn", vmin=-0.5, vmax=0.8)
        axes[2].set_title("NDVI")
        for ax in axes:
            ax.axis("off")
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / "sentinel2_preview.png", dpi=150, bbox_inches="tight")
        plt.show()
        print(f"Saved preview → {OUTPUT_DIR / 'sentinel2_preview.png'}")
    else:
        print("⚠️  B04 or B08 band not found in SAFE directory.")
