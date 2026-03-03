"""
src/auto_training/temporal_contrastive.py
─────────────────────────────────────────────
SimSat: SimCLR for satellites. Learn representations from time.
No labels. Just real satellite pairs and temporal logic.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from typing import Tuple, List
import random

class RandomSpectralDistortion(nn.Module):
    """
    Simulate atmospheric variations between satellite passes.
    Free augmentation that improves robustness.
    """
    def __init__(self, max_distort: float = 0.1):
        super().__init__()
        self.max_distort = max_distort
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Per-band scaling to simulate atmospheric conditions
        # Expects x: (B, C, H, W)
        distort = torch.rand(x.size(0), x.size(1), 1, 1, device=x.device)
        distort = 1 + (distort - 0.5) * 2 * self.max_distort
        return x * distort

class TemporalContrastiveLearner(nn.Module):
    """
    Learn satellite representations by asking:
    "Are these two views of the same place at different times?"
    """
    def __init__(self, 
                 encoder: nn.Module,
                 output_dim: int,
                 projection_dim: int = 128,
                 temperature: float = 0.07):
        super().__init__()
        
        self.encoder = encoder
        self.projector = nn.Sequential(
            nn.Linear(output_dim, 512),
            nn.ReLU(),
            nn.Linear(512, projection_dim)
        )
        
        self.temperature = temperature
        
        self.temporal_augment = transforms.Compose([
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(degrees=15),
            RandomSpectralDistortion()
        ])
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.encoder(x)
        if isinstance(h, torch.Tensor):
            # If ViT, pool or take CLS
            if h.dim() == 3: h = h.mean(dim=1)
        z = F.normalize(self.projector(h), dim=1)
        return z
    
    def nt_xent_loss(self, z_i: torch.Tensor, z_j: torch.Tensor) -> torch.Tensor:
        batch_size = z_i.size(0)
        z = torch.cat([z_i, z_j], dim=0) # (2N, D)
        sim_matrix = torch.mm(z, z.t()) / self.temperature
        mask = torch.eye(2 * batch_size, device=z.device).bool()
        sim_matrix = sim_matrix.masked_fill(mask, -9e15)
        
        positives = torch.cat([
            torch.diag(sim_matrix, batch_size),
            torch.diag(sim_matrix, -batch_size)
        ], dim=0).unsqueeze(1)
        
        logits = torch.cat([positives, sim_matrix], dim=1)
        labels = torch.zeros(2 * batch_size, device=z.device, dtype=torch.long)
        return F.cross_entropy(logits, labels)
