"""
src/auto_training/active_learning_oracle.py
─────────────────────────────────────────────
Model asks for human labels only when uncertain.
Maximize information per human hour.
"""

import torch
import torch.nn as nn
from typing import List, Tuple, Dict

class UncertaintyOracle:
    """
    Active learning: Select most informative samples for labeling.
    """
    def __init__(self, model: nn.Module, strategy: str = 'entropy'):
        self.model = model
        self.strategy = strategy
        
    def identify_uncertain_regions(self, unlabeled_pool: torch.Tensor, top_k: int = 100):
        uncertainties = []
        self.model.train() # Enable dropout if present
        
        with torch.no_grad():
            for idx, image in enumerate(unlabeled_pool):
                preds = []
                for _ in range(5):
                    pred = torch.softmax(self.model(image.unsqueeze(0)), dim=1)
                    preds.append(pred)
                
                preds = torch.stack(preds)
                mean_pred = preds.mean(dim=0)
                entropy = -(mean_pred * torch.log(mean_pred + 1e-8)).sum(dim=1)
                uncertainty = entropy[0] # (H, W)
                
                # Global score for image
                score = uncertainty.mean().item()
                uncertainties.append((idx, score))
        
        uncertainties.sort(key=lambda x: x[1], reverse=True)
        return uncertainties[:top_k]
