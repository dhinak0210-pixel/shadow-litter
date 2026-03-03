"""
tests/benchmark_speed.py
─────────────────────────
Performance profiling — time and memory usage for a full Madurai scan.
Targets: <30s per pair on CPU, <8GB RAM, full 5-zone scan <2hrs.
"""
from __future__ import annotations
import time, sys, logging, tracemalloc
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.models.siamese_unet import ShadowLitterNet

logger = logging.getLogger(__name__)

PATCH_SIZE = 256
N_CHANNELS = 6
IMAGE_SIZE = (N_CHANNELS, 1024, 1024)  # ~10km² tile at 10m/px


def run_inference_benchmark(image_size=IMAGE_SIZE, patch_size=PATCH_SIZE, n_runs=3):
    device = torch.device("cpu")
    model = ShadowLitterNet(N_CHANNELS, 2, pretrained=False).to(device)
    model.eval()

    t1 = np.random.rand(*image_size).astype(np.float32)
    t2 = np.random.rand(*image_size).astype(np.float32)

    stride = patch_size // 2
    C, H, W = image_size
    n_patches = ((H-patch_size)//stride+1) * ((W-patch_size)//stride+1)

    print(f"Image size:  {H}×{W}px | {n_patches} patches / inference")

    times = []
    for run in range(n_runs):
        tracemalloc.start()
        t0 = time.time()

        prob_map = np.zeros((H, W), np.float32)
        count_map = np.zeros((H, W), np.float32)

        with torch.no_grad():
            for y in range(0, H-patch_size+1, stride):
                for x in range(0, W-patch_size+1, stride):
                    p1 = torch.from_numpy(t1[:,y:y+patch_size,x:x+patch_size]).unsqueeze(0)
                    p2 = torch.from_numpy(t2[:,y:y+patch_size,x:x+patch_size]).unsqueeze(0)
                    out = model(p1, p2)
                    change_prob = torch.softmax(out,1)[0,1].numpy()
                    prob_map[y:y+patch_size,x:x+patch_size] += change_prob
                    count_map[y:y+patch_size,x:x+patch_size] += 1

        elapsed = time.time() - t0
        current, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
        times.append(elapsed)
        print(f"Run {run+1}: {elapsed:.1f}s | Peak RAM {peak/1e9:.2f}GB")

    avg = np.mean(times)
    print(f"\nAverage: {avg:.1f}s per image pair")
    print(f"5-zone estimate (4 pairs/zone): {avg*20/3600:.2f} hrs")
    print(f"Target <30s: {'✅ PASS' if avg < 30 else '⚠️ FAIL (expected on CPU without GPU)'}")
    return {"avg_seconds": avg, "n_patches": n_patches}


def benchmark_model_size():
    model = ShadowLitterNet(N_CHANNELS, 2, pretrained=False)
    n_params = sum(p.numel() for p in model.parameters())
    size_mb = n_params * 4 / 1e6  # float32
    print(f"Model: {n_params:,} parameters | {size_mb:.1f} MB")
    return {"params": n_params, "size_mb": size_mb}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("="*50)
    print("  shadow-litter :: Performance Benchmark")
    print("="*50)
    size_info = benchmark_model_size()
    print()
    speed_info = run_inference_benchmark(n_runs=2)
    print("\n✅ Benchmark complete.")
