"""
Segmentation Decoder for Prithvi-100M.
Attaches to the ViT back-end to generate high-resolution waste probability maps.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F

class PrithviSegmentationHead(nn.Module):
    """
    Progressive upsampling decoder for ViT feature maps.
    Converts (Patch_N, Embed_D) features back to (H, W) mask.
    """
    
    def __init__(self, embed_dim: int = 768, patch_size: int = 16, num_classes: int = 1):
        super().__init__()
        self.patch_size = patch_size
        
        # Deconvolutional / PixelShuffle upsampling blocks
        self.upsample1 = nn.Sequential(
            nn.ConvTranspose2d(embed_dim, 256, kernel_size=4, stride=4),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True)
        )
        
        self.upsample2 = nn.Sequential(
            nn.ConvTranspose2d(256, 64, kernel_size=2, stride=2),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True)
        )
        
        self.upsample3 = nn.Sequential(
            nn.ConvTranspose2d(64, 32, kernel_size=2, stride=2),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True)
        )
        
        self.final_conv = nn.Conv2d(32, num_classes, kernel_size=3, padding=1)
        
    def forward(self, x: torch.Tensor, original_size: tuple) -> torch.Tensor:
        """
        x: (B, L, D) — Vision Transformer output tokens
        original_size: (H, W) of the input image
        """
        B, L, D = x.shape
        H_feat = W_feat = int(L**0.5)
        
        # Reshape tokens to 2D feature map
        x = x.transpose(1, 2).reshape(B, D, H_feat, W_feat)
        
        x = self.upsample1(x) # 4x up (e.g. 14->56)
        x = self.upsample2(x) # 2x up (e.g. 56->112)
        x = self.upsample3(x) # 2x up (e.g. 112->224)
        
        # Final sizing to match input perfectly
        x = F.interpolate(x, size=original_size, mode='bilinear', align_corners=False)
        
        return torch.sigmoid(self.final_conv(x))

if __name__ == "__main__":
    # Test shape logic
    head = PrithviSegmentationHead()
    dummy_feat = torch.randn(1, 196, 768) # 14x14 patches = 196
    out = head(dummy_feat, (224, 224))
    print(f"Output shape: {out.shape}") # (1, 1, 224, 224)
