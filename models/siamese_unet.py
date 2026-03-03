import torch
import torch.nn as nn
import torch.nn.functional as F
from einops import rearrange

class AttentionGate(nn.Module):
    """
    Attention mechanism to focus on changed regions.
    Gates skip connections using gating signal from coarser scale.
    """
    
    def __init__(self, F_g, F_l, F_int):
        super().__init__()
        self.W_g = nn.Sequential(
            nn.Conv2d(F_g, F_int, kernel_size=1),
            nn.BatchNorm2d(F_int)
        )
        self.W_x = nn.Sequential(
            nn.Conv2d(F_l, F_int, kernel_size=1),
            nn.BatchNorm2d(F_int)
        )
        self.psi = nn.Sequential(
            nn.Conv2d(F_int, 1, kernel_size=1),
            nn.BatchNorm2d(1),
            nn.Sigmoid()
        )
        self.relu = nn.ReLU(inplace=True)
        
    def forward(self, g, x):
        g1 = self.W_g(g)
        x1 = self.W_x(x)
        psi = self.relu(g1 + x1)
        psi = self.psi(psi)
        return x * psi

class DoubleConv(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.double_conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )
        
    def forward(self, x):
        return self.double_conv(x)

class SiameseUNet(nn.Module):
    """
    Siamese U-Net with Attention for temporal change detection.
    Twin encoders share weights. Difference modules detect changes.
    """
    
    def __init__(self, n_channels=3, n_classes=1, bilinear=True):
        super().__init__()
        self.n_channels = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        
        # Shared Encoder (Siamese twins)
        self.inc = DoubleConv(n_channels, 64)
        self.down1 = self._down_block(64, 128)
        self.down2 = self._down_block(128, 256)
        self.down3 = self._down_block(256, 512)
        factor = 2 if bilinear else 1
        self.down4 = self._down_block(512, 1024 // factor)
        
        # Difference modules at multiple scales
        self.diff_conv1 = self._diff_module(128)
        self.diff_conv2 = self._diff_module(256)
        self.diff_conv3 = self._diff_module(512)
        self.diff_conv4 = self._diff_module(1024 // factor)
        
        # Attention gates
        self.att4 = AttentionGate(1024 // factor, 512, 256)
        self.att3 = AttentionGate(512 // factor, 256, 128)
        self.att2 = AttentionGate(256 // factor, 128, 64)
        self.att1 = AttentionGate(128 // factor, 64, 32)
        
        # Decoder
        self.up1 = self._up_block(1024, 512 // factor, bilinear)
        self.up2 = self._up_block(512, 256 // factor, bilinear)
        self.up3 = self._up_block(256, 128 // factor, bilinear)
        self.up4 = self._up_block(128, 64, bilinear)
        
        # Output
        self.outc = nn.Conv2d(64, n_classes, kernel_size=1)
        self.sigmoid = nn.Sigmoid()
        
    def _down_block(self, in_ch, out_ch):
        return nn.Sequential(
            nn.MaxPool2d(2),
            DoubleConv(in_ch, out_ch)
        )
    
    def _diff_module(self, channels):
        """Compute absolute difference and process"""
        return nn.Sequential(
            nn.Conv2d(channels, channels, 3, padding=1),
            nn.BatchNorm2d(channels),
            nn.ReLU(inplace=True)
        )
    
    def _up_block(self, in_ch, out_ch, bilinear):
        if bilinear:
            up = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
            conv = DoubleConv(in_ch, out_ch)
        else:
            up = nn.ConvTranspose2d(in_ch, in_ch // 2, kernel_size=2, stride=2)
            conv = DoubleConv(in_ch, out_ch)
        return nn.Sequential(up, conv)
    
    def forward(self, x1, x2):
        """
        x1: Before image [B, C, H, W]
        x2: After image [B, C, H, W]
        """
        # Encoder path for x1 (Before)
        x1_1 = self.inc(x1)
        x1_2 = self.down1(x1_1)
        x1_3 = self.down2(x1_2)
        x1_4 = self.down3(x1_3)
        x1_5 = self.down4(x1_4)
        
        # Encoder path for x2 (After) - Shared weights
        x2_1 = self.inc(x2)
        x2_2 = self.down1(x2_1)
        x2_3 = self.down2(x2_2)
        x2_4 = self.down3(x2_3)
        x2_5 = self.down4(x2_4)
        
        # Multi-scale difference detection
        d1 = self.diff_conv1(torch.abs(x1_2 - x2_2))
        d2 = self.diff_conv2(torch.abs(x1_3 - x2_3))
        d3 = self.diff_conv3(torch.abs(x1_4 - x2_4))
        d4 = self.diff_conv4(torch.abs(x1_5 - x2_5))
        
        # Decoder with attention-guided skip connections
        x = self.up1[0](d4)  # Upsample
        x3_att = self.att4(g=x, x=d3)
        x = torch.cat([x3_att, x], dim=1)
        x = self.up1[1](x)
        
        x = self.up2[0](x)
        x2_att = self.att3(g=x, x=d2)
        x = torch.cat([x2_att, x], dim=1)
        x = self.up2[1](x)
        
        x = self.up3[0](x)
        x1_att = self.att2(g=x, x=d1)
        x = torch.cat([x1_att, x], dim=1)
        x = self.up3[1](x)
        
        x = self.up4[0](x)
        x0_att = self.att1(g=x, x=torch.abs(x1_1 - x2_1))
        x = torch.cat([x0_att, x], dim=1)
        x = self.up4[1](x)
        
        logits = self.outc(x)
        return self.sigmoid(logits)
