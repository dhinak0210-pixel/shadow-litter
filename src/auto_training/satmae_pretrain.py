"""
src/auto_training/satmae_pretrain.py
──────────────────────────────────────
SatMAE: Masked autoencoding for satellite time series.
Reconstruct missing patches. Learn spatial-spectral structure.
"""

import torch
import torch.nn as nn
from einops import rearrange

class SatMAE(nn.Module):
    """
    Vision Transformer that reconstructs masked satellite patches.
    """
    def __init__(self,
                 img_size: int = 96,
                 patch_size: int = 8,
                 in_channels: int = 4,
                 embed_dim: int = 768,
                 depth: int = 12,
                 num_heads: int = 12,
                 decoder_embed_dim: int = 512,
                 mask_ratio: float = 0.75):
        super().__init__()
        
        self.patch_size = patch_size
        self.mask_ratio = mask_ratio
        num_patches = (img_size // patch_size) ** 2
        
        self.patch_embed = nn.Conv2d(in_channels, embed_dim, kernel_size=patch_size, stride=patch_size)
        self.pos_embed = nn.Parameter(torch.zeros(1, num_patches, embed_dim))
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim, nhead=num_heads, dim_feedforward=embed_dim * 4, dropout=0.1, batch_first=True
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=depth)
        
        self.decoder_embed = nn.Linear(embed_dim, decoder_embed_dim)
        self.mask_token = nn.Parameter(torch.zeros(1, 1, decoder_embed_dim))
        
        decoder_layer = nn.TransformerEncoderLayer(
            d_model=decoder_embed_dim, nhead=num_heads, dim_feedforward=decoder_embed_dim * 4, batch_first=True
        )
        self.decoder = nn.TransformerEncoder(decoder_layer, num_layers=4)
        self.head = nn.Linear(decoder_embed_dim, patch_size ** 2 * in_channels)
        
    def random_masking(self, x: torch.Tensor, mask_ratio: float):
        N, L, D = x.shape
        len_keep = int(L * (1 - mask_ratio))
        noise = torch.rand(N, L, device=x.device)
        ids_shuffle = torch.argsort(noise, dim=1)
        ids_restore = torch.argsort(ids_shuffle, dim=1)
        ids_keep = ids_shuffle[:, :len_keep]
        x_masked = torch.gather(x, dim=1, index=ids_keep.unsqueeze(-1).expand(-1, -1, D))
        mask = torch.ones([N, L], device=x.device)
        mask[:, :len_keep] = 0
        mask = torch.gather(mask, dim=1, index=ids_restore)
        return x_masked, mask, ids_restore
    
    def forward(self, imgs: torch.Tensor):
        x = self.patch_embed(imgs)
        x = rearrange(x, 'n d h w -> n (h w) d')
        x = x + self.pos_embed
        x_masked, mask, ids_restore = self.random_masking(x, self.mask_ratio)
        latent = self.encoder(x_masked)
        
        mask_tokens = self.mask_token.expand(latent.size(0), ids_restore.size(1) - latent.size(1), -1)
        x_dec = torch.cat([latent, mask_tokens], dim=1)
        x_dec = torch.gather(x_dec, dim=1, index=ids_restore.unsqueeze(-1).expand(-1, -1, latent.size(2)))
        x_dec = self.decoder_embed(x_dec)
        x_dec = self.decoder(x_dec)
        pred = self.head(x_dec)
        
        target = self.patchify(imgs)
        loss = (pred - target) ** 2
        loss = loss.mean(dim=-1)
        loss = (loss * mask).sum() / mask.sum()
        return loss, pred, mask
    
    def patchify(self, imgs: torch.Tensor):
        p = self.patch_size
        h = w = imgs.shape[2] // p
        return rearrange(imgs, 'n c (h p1) (w p2) -> n (h w) (p1 p2 c)', p1=p, p2=p)
