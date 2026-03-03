"""
src/training/self_supervised.py
────────────────────────────────
Self-supervised bootstrap — learns temporal consistency without labels.

Strategy: Contrastive pre-training on unlabeled patch pairs.
  - Stable pixels across time → similar embeddings (positive pairs)
  - Changed pixels → different embeddings (negative pairs)

After pretraining, the encoder has richer features for downstream fine-tuning
with fewer labeled examples.
"""
from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

logger = logging.getLogger(__name__)


# ── Loss ──────────────────────────────────────────────────────────────────────

class TemporalConsistencyLoss(nn.Module):
    """
    Contrastive loss for temporal satellite pair consistency.
    
    Stable pixels: features should be close (positive, label=0)
    Changed pixels: features should be far  (negative, label=1)
    
    Uses margin-based contrastive loss (Hadsell et al., 2006).
    """

    def __init__(self, margin: float = 1.0, reduction: str = "mean"):
        super().__init__()
        self.margin = margin
        self.reduction = reduction

    def forward(
        self,
        emb_t1: torch.Tensor,
        emb_t2: torch.Tensor,
        labels: torch.Tensor,
    ) -> torch.Tensor:
        """
        Args:
            emb_t1:  (B, D) embeddings for time t1
            emb_t2:  (B, D) embeddings for time t2
            labels:  (B,) 0=stable, 1=changed
        """
        dist = F.pairwise_distance(emb_t1, emb_t2, p=2)
        
        # Stable pairs: minimize distance
        pos_loss = (1 - labels) * dist.pow(2)
        # Changed pairs: push beyond margin
        neg_loss = labels * F.relu(self.margin - dist).pow(2)
        
        loss = 0.5 * (pos_loss + neg_loss)
        return loss.mean() if self.reduction == "mean" else loss


# ── Dataset ───────────────────────────────────────────────────────────────────

class UnlabeledPairDataset(Dataset):
    """
    Loads unlabeled (t1, t2) patch pairs from CSV pairs file.
    Generates pseudo-change labels using simple thresholding.
    """

    def __init__(
        self,
        pairs_csv: str,
        patch_size: int = 128,
        transform=None,
    ):
        import csv
        with open(pairs_csv) as f:
            self.pairs = list(csv.DictReader(f))
        self.patch_size = patch_size
        self.transform = transform

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int):
        pair = self.pairs[idx]
        t1 = self._load_patch(pair["t1_path"])
        t2 = self._load_patch(pair["t2_path"])

        # Pseudo-label: large absolute difference = changed
        diff = torch.abs(t1 - t2).mean(dim=0)
        changed = (diff > diff.mean() + diff.std()).float()
        # Flatten to pixel-level label for this pair
        label = int(changed.mean() > 0.05)   # 1 if >5% changed,else 0

        if self.transform:
            t1 = self.transform(t1)
            t2 = self.transform(t2)

        return t1, t2, torch.tensor(label, dtype=torch.float32)

    def _load_patch(self, path: str) -> torch.Tensor:
        arr = np.load(path).astype(np.float32)
        # Crop/resize to patch_size
        _, H, W = arr.shape
        if H > self.patch_size:
            y = random.randint(0, H - self.patch_size)
            x = random.randint(0, W - self.patch_size)
            arr = arr[:, y:y + self.patch_size, x:x + self.patch_size]
        if arr.max() > 1.0:
            arr = arr / 10000.0
        return torch.from_numpy(arr)


# ── Simple Projection Head ────────────────────────────────────────────────────

class ProjectionHead(nn.Module):
    """MLP projection head for contrastive learning."""

    def __init__(self, in_dim: int = 2048, hidden_dim: int = 512, out_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(inplace=True),
            nn.Linear(hidden_dim, out_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# ── Pretraining loop ──────────────────────────────────────────────────────────

def pretrain_encoder(
    pairs_csv: str,
    output_path: str = "models/checkpoints/pretrained_encoder.pth",
    epochs: int = 30,
    batch_size: int = 32,
    lr: float = 1e-3,
    margin: float = 1.0,
    seed: int = 42,
) -> None:
    """
    Pretrain the ShadowLitterNet encoder on unlabeled temporal pairs.
    """
    torch.manual_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Pretraining on: {device}")

    dataset = UnlabeledPairDataset(pairs_csv)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=4)

    from src.models.siamese_unet import ShadowLitterNet
    model = ShadowLitterNet(in_channels=6, num_classes=2, pretrained=True).to(device)

    # Global average pooling to get 2048-d embedding from encoder
    gap = nn.AdaptiveAvgPool2d(1)
    proj_head = ProjectionHead(in_dim=2048, out_dim=128).to(device)

    criterion = TemporalConsistencyLoss(margin=margin)
    optimizer = torch.optim.AdamW(
        list(model.parameters()) + list(proj_head.parameters()),
        lr=lr, weight_decay=1e-4,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    for epoch in range(1, epochs + 1):
        model.train()
        proj_head.train()
        losses = []

        for t1, t2, labels in loader:
            t1, t2, labels = t1.to(device), t2.to(device), labels.to(device)
            optimizer.zero_grad()

            # Extract encoder features at deepest scale
            e4_t1 = model._encode(t1)[-1]   # (B, 2048, H/32, W/32)
            e4_t2 = model._encode(t2)[-1]

            emb_t1 = proj_head(gap(e4_t1).flatten(1))
            emb_t2 = proj_head(gap(e4_t2).flatten(1))

            loss = criterion(emb_t1, emb_t2, labels)
            loss.backward()
            optimizer.step()
            losses.append(loss.item())

        scheduler.step()
        logger.info(f"Epoch {epoch:3d}/{epochs}  loss={np.mean(losses):.4f}")

    # Save encoder state dict
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "encoder_state_dict": {
            k: v for k, v in model.state_dict().items()
            if any(k.startswith(s) for s in ["enc0", "enc1", "enc2", "enc3", "enc4"])
        },
        "epochs": epochs,
    }, out_path)
    logger.info(f"✅ Pretrained encoder saved → {out_path}")


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        print("Usage: python -m src.training.self_supervised <pairs_csv>")
        sys.exit(1)
    pretrain_encoder(sys.argv[1])
