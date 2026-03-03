"""
src/auto_training/temporal_teacher.py
───────────────────────────────────────
Use time itself as a teacher.
Stable pixels = background. Sudden change = candidate.
"""

import torch
from typing import List, Tuple
import numpy as np

class TemporalConsistencyTeacher:
    """
    Self-training using temporal logic.
    """
    def __init__(self, stability_threshold: int = 5, change_persistence: int = 3):
        self.stability_threshold = stability_threshold
        self.change_persistence = change_persistence
        
    def generate_pseudo_labels(self, temporal_stack: torch.Tensor) -> torch.Tensor:
        """
        temporal_stack: (T, C, H, W)
        """
        T, C, H, W = temporal_stack.shape
        variance = torch.var(temporal_stack, dim=0).mean(dim=0)
        stable_mask = variance < 0.01
        change_candidates = variance > 0.05
        
        recent_mean = temporal_stack[-self.change_persistence:].mean(dim=0).mean(dim=0)
        early_mean = temporal_stack[:self.stability_threshold].mean(dim=0).mean(dim=0)
        persistent_change = torch.abs(recent_mean - early_mean) > 0.1
        
        labels = torch.full((H, W), 255, dtype=torch.uint8)
        labels[stable_mask] = 0
        labels[persistent_change & change_candidates] = 1
        return labels
