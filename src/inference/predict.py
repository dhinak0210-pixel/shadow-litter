"""
src/inference/predict.py
────────────────────────
The watching.
Runs the trained model over a full satellite tile using a sliding window,
then converts raw predictions to georeferenced GeoJSON polygons.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Generator

import numpy as np
import torch
import rasterio
from rasterio.transform import from_bounds
import geopandas as gpd
from shapely.geometry import shape
from skimage import measure
import json
import yaml

from src.models.segmentation import build_model, load_checkpoint

logger = logging.getLogger(__name__)


def load_config(path: str = "configs/config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def sliding_window(
    arr: np.ndarray,
    patch_size: int,
    overlap: int
) -> Generator[tuple[int, int, np.ndarray], None, None]:
    """Yield (y, x, patch) for sliding window over (C, H, W) array."""
    _, H, W = arr.shape
    stride = patch_size - overlap
    for y in range(0, max(H - patch_size + 1, 1), stride):
        for x in range(0, max(W - patch_size + 1, 1), stride):
            yield y, x, arr[:, y:y + patch_size, x:x + patch_size]


def predict_tile(
    image_path: str,
    checkpoint_path: str,
    config_path: str = "configs/config.yaml",
    output_geojson: str = "outputs/detections.geojson",
) -> str:
    """
    Run inference on a single multi-band GeoTIFF and output GeoJSON detections.

    Args:
        image_path:       Path to stacked multi-band GeoTIFF
        checkpoint_path:  Path to model .pt checkpoint
        config_path:      Path to config YAML
        output_geojson:   Where to write detection results

    Returns:
        Path to output GeoJSON file
    """
    cfg = load_config(config_path)
    pre = cfg["preprocessing"]
    inf = cfg["inference"]
    m_cfg = cfg["model"]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Inference on: {device}")

    # ── load model
    model = build_model(config_path).to(device)
    model = load_checkpoint(model, checkpoint_path)
    model.eval()

    # ── load image
    with rasterio.open(image_path) as src:
        arr = src.read().astype(np.float32)   # (C, H, W)
        transform = src.transform
        crs = src.crs
        H, W = src.height, src.width

    # normalize
    p2, p98 = np.percentile(arr, 2), np.percentile(arr, 98)
    arr = np.clip(arr, p2, p98)
    arr = (arr - p2) / (p98 - p2 + 1e-8)

    # ── sliding window inference
    patch_size = pre["patch_size"]
    overlap = pre["overlap"]
    prob_map = np.zeros((m_cfg["num_classes"], H, W), dtype=np.float32)
    count_map = np.zeros((H, W), dtype=np.float32)

    with torch.no_grad():
        for y, x, patch in sliding_window(arr, patch_size, overlap):
            ph, pw = patch.shape[1], patch.shape[2]
            tensor = torch.from_numpy(patch).unsqueeze(0).to(device)
            out = model(tensor).squeeze(0).cpu().numpy()  # (num_classes, ph, pw)
            prob_map[:, y:y + ph, x:x + pw] += out
            count_map[y:y + ph, x:x + pw] += 1

    count_map = np.maximum(count_map, 1)
    prob_map /= count_map[np.newaxis, :, :]

    # ── threshold waste class (class 1 = waste_site, class 2 = illegal_dump)
    waste_prob = prob_map[1] + prob_map[2]
    binary_mask = (waste_prob >= inf["confidence_threshold"]).astype(np.uint8)

    # ── vectorize mask to polygons
    features = []
    contours = measure.find_contours(binary_mask, 0.5)
    pixel_area = abs(transform.a * transform.e)  # m² per pixel

    for contour in contours:
        # convert pixel coords to geo coords
        coords = []
        for r, c in contour:
            x_geo, y_geo = transform * (c, r)
            coords.append((x_geo, y_geo))
        if len(coords) < 4:
            continue
        coords.append(coords[0])  # close polygon

        from shapely.geometry import Polygon
        poly = Polygon(coords)
        area_m2 = poly.area

        if area_m2 < inf["min_area_m2"]:
            continue

        # get max waste probability in this polygon bbox
        row_min = int(min(r for r, c in contour))
        row_max = int(max(r for r, c in contour)) + 1
        col_min = int(min(c for r, c in contour))
        col_max = int(max(c for r, c in contour)) + 1
        confidence = float(waste_prob[row_min:row_max, col_min:col_max].max())

        features.append({
            "type": "Feature",
            "geometry": poly.__geo_interface__,
            "properties": {
                "confidence": round(confidence, 4),
                "area_m2": round(area_m2, 2),
                "waste_class": "illegal_dump" if prob_map[2, row_min, col_min] > prob_map[1, row_min, col_min] else "waste_site",
            }
        })

    geojson = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": str(crs)}},
        "features": features,
    }

    out_path = Path(output_geojson)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(geojson, indent=2))

    logger.info(f"✅ {len(features)} detections written → {out_path}")
    return str(out_path)


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Run waste detection inference")
    parser.add_argument("--image", required=True, help="Path to stacked GeoTIFF")
    parser.add_argument("--checkpoint", required=True, help="Path to .pt checkpoint")
    parser.add_argument("--output", default="outputs/detections.geojson")
    parser.add_argument("--config", default="configs/config.yaml")
    args = parser.parse_args()
    predict_tile(args.image, args.checkpoint, args.config, args.output)
