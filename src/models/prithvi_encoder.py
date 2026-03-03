"""
NASA Prithvi-100M: Foundation model for remote sensing.
100M parameters, pre-trained on 250k+ Sentinel-2 images.
Real transfer learning from real satellite intelligence.
"""

import torch
import torch.nn as nn
from transformers import AutoModel, AutoConfig
from typing import Tuple

class PrithviEncoder(nn.Module):
    """
    Prithvi-EO-2.0: 300M parameters, pre-trained on Sentinel-2 time series.
    NASA/IBM Foundation Model for real-world change detection.
    """
    
    def __init__(self, pretrained: bool = True, num_frames: int = 2):
        super().__init__()
        
        # Latest Prithvi-2.0 from HuggingFace
        model_name = "ibm-nasa-geospatial/Prithvi-EO-2.0-300M"
        
        if pretrained:
            self.backbone = AutoModel.from_pretrained(
                model_name,
                trust_remote_code=True,
                num_frames=num_frames
            )
        else:
            config = AutoConfig.from_pretrained(model_name, trust_remote_code=True)
            self.backbone = AutoModel.from_config(config)
            
        # Freeze early blocks for stable fine-tuning
        for i, block in enumerate(self.backbone.encoder.blocks):
            if i < 12: # Freeze first half of the large ViT
                for param in block.parameters():
                    param.requires_grad = False
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (B, C, T, H, W) 
        Returns: (B, T, L, D) features
        """
        # Prithvi-2.0 handles temporal frames natively
        return self.backbone(x).last_hidden_state

# Integration Notes:
# Real Sentinel-2 bands for Prithvi: [Blue, Green, Red, Edge1, Edge2, Edge3, NIR, SWIR1, SWIR2]
# The model is highly sensitive to the spectral signature of waste vs soil.

