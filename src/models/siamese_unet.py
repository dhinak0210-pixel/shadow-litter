"""
src/models/siamese_unet.py
───────────────────────────
ShadowLitterNet — Siamese U-Net for bi-temporal change detection.

Architecture:
  • Shared ResNet-50 encoder (ImageNet pretrained)
  • Two branches process (t1, t2) simultaneously
  • Difference module: L1 + channel-wise attention
  • U-Net style decoder with skip connections
  • Output: 2-channel change probability map (no-change, change)
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision.models import resnet50, ResNet50_Weights


# ── Channel-wise Attention ─────────────────────────────────────────────────────

class ChannelAttention(nn.Module):
    """Squeeze-and-Excitation channel attention block."""

    def __init__(self, channels: int, reduction: int = 16):
        super().__init__()
        self.gap = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(
            nn.Linear(channels, channels // reduction, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(channels // reduction, channels, bias=False),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, c, _, _ = x.shape
        attn = self.gap(x).view(b, c)
        attn = self.fc(attn).view(b, c, 1, 1)
        return x * attn


# ── Difference Module ──────────────────────────────────────────────────────────

class DifferenceModule(nn.Module):
    """
    Combines features from two temporal branches.
    Uses L1 absolute difference + channel attention to highlight changes.
    """

    def __init__(self, channels: int):
        super().__init__()
        self.attention = ChannelAttention(channels)
        self.conv = nn.Sequential(
            nn.Conv2d(channels * 2, channels, kernel_size=1, bias=False),
            nn.BatchNorm2d(channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, feat_t1: torch.Tensor, feat_t2: torch.Tensor) -> torch.Tensor:
        diff = torch.abs(feat_t1 - feat_t2)
        diff = self.attention(diff)
        combined = torch.cat([diff, feat_t1 + feat_t2], dim=1)
        return self.conv(combined)


# ── Decoder Block ──────────────────────────────────────────────────────────────

class DecoderBlock(nn.Module):
    """U-Net style upsampling block with skip connection."""

    def __init__(self, in_ch: int, skip_ch: int, out_ch: int):
        super().__init__()
        self.up = nn.ConvTranspose2d(in_ch, out_ch, kernel_size=2, stride=2)
        self.conv = nn.Sequential(
            nn.Conv2d(out_ch + skip_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        x = self.up(x)
        if x.shape != skip.shape:
            x = F.interpolate(x, size=skip.shape[2:], mode="bilinear", align_corners=False)
        x = torch.cat([x, skip], dim=1)
        return self.conv(x)


# ── Main Model ─────────────────────────────────────────────────────────────────

class ShadowLitterNet(nn.Module):
    """
    Siamese U-Net for bi-temporal waste dump change detection.

    Input:  (B, C, H, W) at t1 and t2  (C = in_channels = 6 for Sentinel-2)
    Output: (B, 2, H, W) change probability logits
    """

    IN_CHANNELS = 6    # B02 B03 B04 B08 B11 B12

    def __init__(
        self,
        in_channels: int = 6,
        num_classes: int = 2,
        pretrained: bool = True,
    ):
        super().__init__()
        self.in_channels = in_channels
        self.num_classes = num_classes

        # ── Shared ResNet-50 encoder ──────────────────────────────────────────
        weights = ResNet50_Weights.IMAGENET1K_V2 if pretrained else None
        backbone = resnet50(weights=weights)

        # Adapt first conv if in_channels != 3
        if in_channels != 3:
            backbone.conv1 = nn.Conv2d(
                in_channels, 64, kernel_size=7, stride=2, padding=3, bias=False
            )
            if pretrained and in_channels > 3:
                with torch.no_grad():
                    backbone.conv1.weight[:, :3] = resnet50(
                        weights=ResNet50_Weights.IMAGENET1K_V2
                    ).conv1.weight
            nn.init.kaiming_normal_(backbone.conv1.weight, mode="fan_out", nonlinearity="relu")

        # Extract encoder stages for skip connections
        self.enc0 = nn.Sequential(backbone.conv1, backbone.bn1, backbone.relu)  # /2  64ch
        self.pool  = backbone.maxpool                                             # /4
        self.enc1  = backbone.layer1   # /4   256ch
        self.enc2  = backbone.layer2   # /8   512ch
        self.enc3  = backbone.layer3   # /16  1024ch
        self.enc4  = backbone.layer4   # /32  2048ch

        # ── Difference modules at each scale ─────────────────────────────────
        self.diff4 = DifferenceModule(2048)
        self.diff3 = DifferenceModule(1024)
        self.diff2 = DifferenceModule(512)
        self.diff1 = DifferenceModule(256)
        self.diff0 = DifferenceModule(64)

        # ── Decoder ───────────────────────────────────────────────────────────
        self.dec4 = DecoderBlock(2048, 1024, 512)
        self.dec3 = DecoderBlock(512,  512,  256)
        self.dec2 = DecoderBlock(256,  256,  128)
        self.dec1 = DecoderBlock(128,  64,   64)

        # ── Final head ────────────────────────────────────────────────────────
        self.head = nn.Sequential(
            nn.Conv2d(64, 32, 3, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, num_classes, 1),
        )

    # ── Encode one image ──────────────────────────────────────────────────────

    def _encode(self, x: torch.Tensor) -> tuple:
        e0 = self.enc0(x)          # 64,  H/2,  W/2
        p  = self.pool(e0)         # 64,  H/4,  W/4
        e1 = self.enc1(p)          # 256, H/4,  W/4
        e2 = self.enc2(e1)         # 512, H/8,  W/8
        e3 = self.enc3(e2)         # 1024,H/16, W/16
        e4 = self.enc4(e3)         # 2048,H/32, W/32
        return e0, e1, e2, e3, e4

    def forward(self, img_t1: torch.Tensor, img_t2: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            img_t1: (B, C, H, W) earlier date image
            img_t2: (B, C, H, W) later date image

        Returns:
            (B, num_classes, H, W) change logits
        """
        # Encode both images with shared weights
        e0_t1, e1_t1, e2_t1, e3_t1, e4_t1 = self._encode(img_t1)
        e0_t2, e1_t2, e2_t2, e3_t2, e4_t2 = self._encode(img_t2)

        # Build difference features at each scale
        d4 = self.diff4(e4_t1, e4_t2)
        d3 = self.diff3(e3_t1, e3_t2)
        d2 = self.diff2(e2_t1, e2_t2)
        d1 = self.diff1(e1_t1, e1_t2)
        d0 = self.diff0(e0_t1, e0_t2)

        # Decode with skip connections
        x = self.dec4(d4, d3)
        x = self.dec3(x,  d2)
        x = self.dec2(x,  d1)
        x = self.dec1(x,  d0)

        # Upsample to input resolution
        x = F.interpolate(x, scale_factor=2, mode="bilinear", align_corners=False)
        return self.head(x)

    @property
    def n_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())


if __name__ == "__main__":
    import sys
    model = ShadowLitterNet(in_channels=6, num_classes=2, pretrained=False)
    print(f"ShadowLitterNet  |  {model.n_parameters:,} parameters")

    # Smoke test
    t1 = torch.zeros(2, 6, 256, 256)
    t2 = torch.zeros(2, 6, 256, 256)
    out = model(t1, t2)
    print(f"Input shape:  {t1.shape}")
    print(f"Output shape: {out.shape}")   # expect (2, 2, 256, 256)
    assert out.shape == (2, 2, 256, 256), f"Shape mismatch: {out.shape}"
    print("✅ Forward pass OK")
