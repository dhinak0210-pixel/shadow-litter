import torch
from torch.utils.data import Dataset
import numpy as np
from training.synthetic_generator import DumpSynthesizer
from data_engine.sentinel_hub import SentinelFeed
import os

class ShadowLitterDataset(Dataset):
    """
    Real-world background data + Synthetic waste dump augmentation.
    """
    def __init__(self, background_patches=None, transform=None, n_samples=1000):
        self.synth = DumpSynthesizer(image_size=256)
        self.n_samples = n_samples
        self.background_patches = background_patches
        
        if self.background_patches is None:
            # Create dummy backgrounds if none provided for bootstrap
            self.background_patches = [
                np.random.uniform(50, 150, (256, 256, 3)).astype(np.float32)
                for _ in range(10)
            ]
            
    def __len__(self):
        return self.n_samples
        
    def __getitem__(self, idx):
        # Pick a random background patch
        bg_idx = np.random.randint(0, len(self.background_patches))
        clean_patch = self.background_patches[bg_idx]
        
        # Synthesize pair
        before, after, mask = self.synth.synthesize_pair(clean_patch)
        
        return before, after, mask

def collect_real_backgrounds(n_patches=50):
    """
    Downloads real Sentinel-2 imagery for Madurai and extracts clean patches.
    """
    print("Collecting real background patches from Sentinel-2...")
    feed = SentinelFeed()
    
    # Get recent clear imagery
    scenes = feed.search_temporal_stack("2025-01-01T00:00:00Z", "2026-02-28T00:00:00Z", cloud_cover=5.0)
    if not scenes:
        return None
        
    best_scene = scenes[0]
    bands = feed.download_bands(best_scene, ['B04', 'B08', 'B11'])
    # bands shape [3, 1098, 1098]. Normalize for better training
    bands = bands.astype(np.float32) / 10000.0 
    bands = np.clip(bands * 255, 0, 255) # Scale to 0-255 range for synthesizer logic
    
    image = bands.transpose(1, 2, 0) # [H, W, 3]
    
    patches = []
    h, w = image.shape[:2]
    patch_size = 256
    
    for _ in range(n_patches):
        y = np.random.randint(0, h - patch_size)
        x = np.random.randint(0, w - patch_size)
        patch = image[y:y+patch_size, x:x+patch_size]
        patches.append(patch)
        
    return patches
