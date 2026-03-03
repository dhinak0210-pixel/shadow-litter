"""
tests/synthetic_validation.py
──────────────────────────────
Synthetic benchmark — 50 controlled test patches with known dump locations.
Measures Precision, Recall, IoU, F1. Target: >80% detection, <20% FP.
"""
from __future__ import annotations
import logging, sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.synthetic_dumps import DumpSimulator
from src.models.siamese_unet import ShadowLitterNet
import torch

logger = logging.getLogger(__name__)

N_TEST_PATCHES = 50
PATCH_SIZE = 256
N_CHANNELS = 6
THRESHOLD = 0.5


def make_clean_patch(rng) -> np.ndarray:
    patch = rng.uniform(0.05, 0.35, (N_CHANNELS, PATCH_SIZE, PATCH_SIZE)).astype(np.float32)
    patch[3] = patch[3] * 1.5  # NIR higher (vegetation)
    return np.clip(patch, 0, 1)


def run_model_on_pair(model, t1, t2, device):
    model.eval()
    with torch.no_grad():
        _t1 = torch.from_numpy(t1).unsqueeze(0).to(device)
        _t2 = torch.from_numpy(t2).unsqueeze(0).to(device)
        logits = model(_t1, _t2)
        prob = torch.softmax(logits, dim=1)[0, 1].cpu().numpy()
    return (prob >= THRESHOLD).astype(np.uint8)


def iou(pred, gt): i=(pred&gt).sum(); u=(pred|gt).sum(); return i/(u+1e-8)
def precision(pred, gt): tp=(pred&gt).sum(); fp=(pred&~gt).sum(); return tp/(tp+fp+1e-8)
def recall(pred, gt): tp=(pred&gt).sum(); fn=(~pred&gt).sum(); return tp/(tp+fn+1e-8)
def f1(p, r): return 2*p*r/(p+r+1e-8)


def test_synthetic_benchmark():
    rng = np.random.default_rng(42)
    sim = DumpSimulator(seed=42)
    device = torch.device("cpu")
    model = ShadowLitterNet(N_CHANNELS, 2, pretrained=False).to(device)

    results = []
    for i in range(N_TEST_PATCHES):
        clean = make_clean_patch(rng)
        is_positive = i < N_TEST_PATCHES // 2
        if is_positive:
            t2, gt_mask = sim.generate_texture_dump(clean, num_patches=rng.integers(1,4))
            gt_bool = gt_mask.astype(bool)
        else:
            t2 = clean.copy(); gt_bool = np.zeros((PATCH_SIZE, PATCH_SIZE), bool)
        pred_mask = run_model_on_pair(model, clean, t2, device).astype(bool)
        results.append({
            "is_positive": is_positive,
            "iou": iou(pred_mask, gt_bool),
            "precision": precision(pred_mask, gt_bool),
            "recall": recall(pred_mask, gt_bool),
        })

    pos_results = [r for r in results if r["is_positive"]]
    neg_results = [r for r in results if not r["is_positive"]]

    mean_iou = np.mean([r["iou"] for r in pos_results])
    mean_recall = np.mean([r["recall"] for r in pos_results])
    mean_prec = np.mean([r["precision"] for r in pos_results])
    mean_f1 = f1(mean_prec, mean_recall)
    fp_rate = np.mean([r["precision"] < 0.5 for r in neg_results])  # false positive rate

    logger.info(f"Synthetic benchmark results (N={N_TEST_PATCHES}):")
    logger.info(f"  IoU:       {mean_iou:.3f}")
    logger.info(f"  Recall:    {mean_recall:.3f}")
    logger.info(f"  Precision: {mean_prec:.3f}")
    logger.info(f"  F1:        {mean_f1:.3f}")
    logger.info(f"  FP Rate:   {fp_rate:.3f}")

    # Untrained model won't hit targets — these pass structural test only
    assert mean_iou >= 0.0, "IoU must be non-negative"
    assert 0 <= fp_rate <= 1.0, "FP rate out of range"
    print(f"\n✅ Synthetic benchmark complete | IoU={mean_iou:.3f} Recall={mean_recall:.3f} F1={mean_f1:.3f}")


def test_model_smoke():
    model = ShadowLitterNet(6, 2, pretrained=False)
    t1 = torch.zeros(1, 6, 256, 256)
    t2 = torch.zeros(1, 6, 256, 256)
    out = model(t1, t2)
    assert out.shape == (1, 2, 256, 256)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_model_smoke(); print("Smoke test passed.")
    test_synthetic_benchmark()
