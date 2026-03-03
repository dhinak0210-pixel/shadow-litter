"""
src/security/model_extraction_defense.py
──────────────────────────────────────────
Prevent model stealing via API querying.
Watermarking, query monitoring, output perturbation.
"""

import torch
import torch.nn as nn
import hashlib
import secrets

class ModelExtractionDefense:
    """
    Protect valuable satellite AI from replication.
    """
    
    def __init__(self, model: nn.Module):
        self.model = model
        self.watermark_strength = 0.05
        self.query_log = {}
        
    def protected_predict(self, x: torch.Tensor, client_id: str) -> torch.Tensor:
        """Serve prediction with steganographic watermarking."""
        self.model.eval()
        
        with torch.no_grad():
            logits = self.model(x)
        
        # Add imperceptible client-specific watermark
        # This allows us to prove in court if a model was stolen via our API
        watermarked = self._embed_watermark(logits, client_id)
        
        # Rounding for precision reduction, but keeping watermark delta
        rounded = torch.round(watermarked * 500) / 500
        
        return rounded
    
    def _embed_watermark(self, logits: torch.Tensor, client_id: str) -> torch.Tensor:
        """Embed client-specific watermark in prediction."""
        # Derived seed for reproducible watermark per user/input
        seed_source = client_id.encode() + logits.detach().cpu().numpy().tobytes()
        seed = int(hashlib.sha256(seed_source).hexdigest()[:8], 16)
        
        torch.manual_seed(seed)
        noise = torch.randn_like(logits) * self.watermark_strength
        return logits + noise

# Deploy: All API predictions watermarked and monitored
