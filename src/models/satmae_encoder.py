"""
SatMAE: Masked Autoencoding for Satellite Imagery.
CVPR 2023. Pre-trained on real Sentinel-2 global dataset.
"""

import torch
import torch.nn as nn
import timm
from typing import Optional

class SatMAEEncoder(nn.Module):
    """
    ViT-Base/16 encoder with satellite-specific pre-training.
    Better than ImageNet for remote sensing tasks.
    """
    
    def __init__(self, model_name: str = "vit_base_patch16_224"):
        super().__init__()
        
        # Load SatMAE weights (available on HuggingFace)
        self.encoder = timm.create_model(
            model_name,
            pretrained=False,
            num_classes=0,  # Remove head
            in_chans=13,    # Sentinel-2 13 bands
            img_size=96     # Native patch size for Sentinel
        )
        
        # Load SatMAE pre-trained weights
        satmae_ckpt = torch.load("weights/satmae_vit_base_96.pth")
        self.encoder.load_state_dict(satmae_ckpt, strict=False)
        
        # Adapt to 4-band input (RGB+NIR) with band embedding
        self.band_embed = nn.Conv2d(4, 13, 1)  # Project 4 -> 13 bands
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (B, 4, H, W) — RGB+NIR
        Returns: (B, 768) or (B, 768, H//16, W//16) if feature extraction
        """
        # Project to 13 bands
        x = self.band_embed(x)
        
        # Patch embedding happens in encoder
        features = self.encoder.forward_features(x)
        return features

# SatMAE captures seasonal patterns, cloud shadows, terrain — real satellite physics.
