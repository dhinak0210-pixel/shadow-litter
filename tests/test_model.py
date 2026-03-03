"""
tests/test_model.py
────────────────────
Validation prayers — smoke tests for the model pipeline.
"""
import torch
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.segmentation import build_model


def test_model_builds():
    """Model should build without error."""
    model = build_model()
    assert model is not None


def test_model_forward_pass():
    """Model should produce output of correct shape."""
    model = build_model()
    model.eval()
    # 6 channels = B02 B03 B04 B08 B11 B12
    dummy_input = torch.zeros(1, 6, 256, 256)
    with torch.no_grad():
        out = model(dummy_input)
    # Expected: (batch, num_classes, H, W)
    assert out.shape == (1, 3, 256, 256), f"Unexpected output shape: {out.shape}"


def test_output_probabilities():
    """Output probabilities should sum to ~1 across class dimension."""
    model = build_model()
    model.eval()
    dummy_input = torch.rand(2, 6, 256, 256)
    with torch.no_grad():
        out = model(dummy_input)
    sums = out.sum(dim=1)
    assert torch.allclose(sums, torch.ones_like(sums), atol=1e-5), \
        "Softmax probabilities do not sum to 1"
