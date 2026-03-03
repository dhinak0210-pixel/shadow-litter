import os
import sys
from pathlib import Path
import torch

def verify_all():
    print("🔍 RUNNING PRE-FLIGHT CHECKS...")
    
    # 1. Credentials
    creds = ["COPERNICUS_USER", "COPERNICUS_PASS"]
    for c in creds:
        if not os.getenv(c):
            print(f"❌ ERROR: {c} not set.")
            sys.exit(1)
        print(f"✅ {c} is set.")
    
    # 2. Model Weights
    models = [
        "models/final/siamese_best.pth"
    ]
    for m in models:
        if not Path(m).exists():
            print(f"❌ ERROR: Model {m} not found.")
            sys.exit(1)
        print(f"✅ Model found: {m} ({Path(m).stat().st_size / 1e6:.1f} MB)")
    
    # 3. GPU
    if not torch.cuda.is_available():
        print("⚠️  WARNING: GPU not available. Running on CPU (Inference will be slow).")
    else:
        print(f"✅ GPU available: {torch.cuda.get_device_name(0)}")
        
    print("🚀 PRE-FLIGHT CHECKS PASSED.")

if __name__ == "__main__":
    verify_all()
