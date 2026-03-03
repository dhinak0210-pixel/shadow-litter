"""
src/inference/predict_change.py
────────────────────────────────
Full end-to-end change detection pipeline.
Loads a (t1, t2) image pair → runs ShadowLitterNet → returns GeoDataFrame.
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional
import numpy as np
import torch
import rasterio
from skimage import measure
from shapely.geometry import Polygon
import geopandas as gpd

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.75
MIN_AREA_M2 = 500


def _load_and_normalize(path: str, H: int = None, W: int = None) -> tuple:
    with rasterio.open(path) as src:
        arr = src.read().astype(np.float32)
        transform = src.transform; crs = src.crs
    if H and arr.shape[1] != H:
        import cv2
        arr = np.stack([cv2.resize(arr[c], (W, H), interpolation=cv2.INTER_LINEAR) for c in range(arr.shape[0])])
    p2, p98 = np.percentile(arr, 2), np.percentile(arr, 98)
    arr = np.clip(arr, p2, p98) / (p98 - p2 + 1e-8)
    return arr, transform, crs


def detect_dumps(
    t1_path: str,
    t2_path: str,
    model=None,
    model_checkpoint: str = "models/final/siamese_best.pth",
    config_path: str = "configs/config.yaml",
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
    min_area_m2: float = MIN_AREA_M2,
    output_geojson: Optional[str] = None,
) -> gpd.GeoDataFrame:
    import yaml
    cfg = yaml.safe_load(open(config_path))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load model if not provided
    if model is None:
        from src.models.siamese_unet import ShadowLitterNet
        from src.models.spectral_classifier import DumpTypeClassifier
        model = ShadowLitterNet(6, 2, pretrained=False).to(device)
        if Path(model_checkpoint).exists():
            state = torch.load(model_checkpoint, map_location="cpu")
            model.load_state_dict(state["model"]); logger.info(f"Loaded {model_checkpoint}")
        model.eval()

    # Load both images
    t1, transform, crs = _load_and_normalize(t1_path)
    _, H, W = t1.shape
    t2, _, _ = _load_and_normalize(t2_path, H, W)

    # Sliding window inference
    ps = cfg["preprocessing"]["patch_size"]
    stride = ps // 2
    prob_map = np.zeros((H, W), dtype=np.float32)
    count_map = np.zeros((H, W), dtype=np.float32)

    with torch.no_grad():
        for y in range(0, max(H - ps + 1, 1), stride):
            for x in range(0, max(W - ps + 1, 1), stride):
                p1 = torch.from_numpy(t1[:, y:y+ps, x:x+ps]).unsqueeze(0).to(device)
                p2 = torch.from_numpy(t2[:, y:y+ps, x:x+ps]).unsqueeze(0).to(device)
                logits = model(p1, p2)
                change_prob = torch.softmax(logits, dim=1)[0, 1].cpu().numpy()
                ph, pw = change_prob.shape
                prob_map[y:y+ph, x:x+pw] += change_prob
                count_map[y:y+ph, x:x+pw] += 1

    prob_map /= np.maximum(count_map, 1)
    binary = (prob_map >= confidence_threshold).astype(np.uint8)

    # Vectorize
    features = []
    for contour in measure.find_contours(binary, 0.5):
        coords = [transform * (c, r) for r, c in contour]
        if len(coords) < 4: continue
        coords.append(coords[0])
        poly = Polygon(coords)
        if poly.area < min_area_m2: continue
        r_min = int(min(r for r, _ in contour)); c_min = int(min(c for _, c in contour))
        conf = float(prob_map[r_min, c_min])
        # Spectral classification
        region = t2[:, max(0, r_min-20):r_min+20, max(0, c_min-20):c_min+20]
        dump_type = _classify_spectral(region)
        features.append({
            "geometry": poly,
            "confidence": round(conf, 4),
            "area_sqm": round(poly.area, 2),
            "dump_type": dump_type,
        })

    gdf = gpd.GeoDataFrame(features, crs=str(crs)) if features else gpd.GeoDataFrame(columns=["geometry","confidence","area_sqm","dump_type"])

    if output_geojson and len(gdf) > 0:
        Path(output_geojson).parent.mkdir(parents=True, exist_ok=True)
        gdf.to_file(output_geojson, driver="GeoJSON")
        logger.info(f"✅ {len(gdf)} detections → {output_geojson}")

    return gdf


def _classify_spectral(region: np.ndarray) -> str:
    """Quick heuristic spectral classification (fallback to RF classifier)."""
    if region.shape[1] < 5 or region.shape[2] < 5: return "unknown"
    b = region.mean(axis=(1, 2))
    nir = b[3] if len(b) > 3 else 0
    swir = b[4] if len(b) > 4 else 0
    if nir < 0.1: return "leachate"
    if swir > 0.6: return "construction_debris"
    return "fresh_dump"


if __name__ == "__main__":
    import argparse, sys
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser()
    p.add_argument("--t1", required=True); p.add_argument("--t2", required=True)
    p.add_argument("--output", default="outputs/detections.geojson")
    p.add_argument("--checkpoint", default="models/final/siamese_best.pth")
    args = p.parse_args()
    gdf = detect_dumps(args.t1, args.t2, model_checkpoint=args.checkpoint, output_geojson=args.output)
    print(f"{len(gdf)} detections found.")
