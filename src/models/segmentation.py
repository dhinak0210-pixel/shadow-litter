"""
src/models/segmentation.py
──────────────────────────
Neural architecture factory.
Builds a segmentation model from config using segmentation-models-pytorch.
Supports: Unet, UnetPlusPlus, DeepLabV3+, FPN, PAN.
"""
from __future__ import annotations

import logging
from pathlib import Path

import torch
import torch.nn as nn
import segmentation_models_pytorch as smp
import yaml

logger = logging.getLogger(__name__)

SUPPORTED_ARCHITECTURES = {
    "Unet": smp.Unet,
    "UnetPlusPlus": smp.UnetPlusPlus,
    "DeepLabV3Plus": smp.DeepLabV3Plus,
    "FPN": smp.FPN,
    "PAN": smp.PAN,
}


def load_config(path: str = "configs/config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def build_model(config_path: str = "configs/config.yaml") -> nn.Module:
    """Construct and return the segmentation model from config."""
    cfg = load_config(config_path)
    m = cfg["model"]

    arch_name = m["architecture"]
    if arch_name not in SUPPORTED_ARCHITECTURES:
        raise ValueError(
            f"Unknown architecture '{arch_name}'. "
            f"Choose from: {list(SUPPORTED_ARCHITECTURES.keys())}"
        )

    arch_cls = SUPPORTED_ARCHITECTURES[arch_name]
    model = arch_cls(
        encoder_name=m["encoder"],
        encoder_weights=m["encoder_weights"],
        in_channels=m["in_channels"],
        classes=m["num_classes"],
        activation=m["activation"],
    )

    logger.info(
        f"Built {arch_name} | encoder={m['encoder']} | "
        f"in_channels={m['in_channels']} | classes={m['num_classes']}"
    )
    return model


def load_checkpoint(model: nn.Module, checkpoint_path: str) -> nn.Module:
    """Load weights from a checkpoint file."""
    path = Path(checkpoint_path)
    if not path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {path}")
    state = torch.load(path, map_location="cpu")
    model.load_state_dict(state["model_state_dict"])
    logger.info(f"Loaded checkpoint from {path} (epoch {state.get('epoch', '?')})")
    return model


def save_checkpoint(
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    epoch: int,
    loss: float,
    out_path: str,
) -> None:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "loss": loss,
        },
        out_path,
    )
    logger.info(f"Checkpoint saved → {out_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    model = build_model()
    total = sum(p.numel() for p in model.parameters())
    logger.info(f"Total parameters: {total:,}")
