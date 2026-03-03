"""
PyTorch Lightning Module for fine-tuning NASA Prithvi on real waste labels.
"""
import torch
import torch.nn as nn
import pytorch_lightning as pl
from src.models.prithvi_encoder import PrithviEncoder
from src.models.segmentation_head import PrithviSegmentationHead

class ShadowLitterModel(pl.LightningModule):
    def __init__(self, lr: float = 1e-4):
        super().__init__()
        self.save_hyperparameters()
        
        # Load the Foundation Model
        self.encoder = PrithviEncoder(pretrained=True, freeze_blocks=8)
        
        # Add the Segmentation Head (Waste detection focus)
        self.decoder = PrithviSegmentationHead(embed_dim=768) 
        
        # Specialized Change Detection Loss for extreme imbalance
        self.criterion = self._build_loss()
        
    def _build_loss(self):
        """Dice + Focal loss to handle the 99:1 background-to-waste imbalance."""
        import segmentation_models_pytorch as smp
        dice = smp.losses.DiceLoss(mode='binary', from_logits=False)
        focal = smp.losses.FocalLoss(mode='binary', alpha=0.8, gamma=2.0)
        return lambda p, t: dice(p, t) + 2.0 * focal(p, t)
        
    def forward(self, x):
        # x: (B, 6, T, H, W)
        feats = self.encoder(x) # (B, L, D)
        mask_pred = self.decoder(feats, (x.shape[3], x.shape[4]))
        return mask_pred
        
    def training_step(self, batch, batch_idx):
        images, masks = batch
        preds = self(images)
        loss = self.criterion(preds, masks)
        self.log("train_loss", loss, prog_bar=True)
        return loss
        
    def validation_step(self, batch, batch_idx):
        images, masks = batch
        preds = self(images)
        loss = self.criterion(preds, masks)
        
        # Calculate IoU (Intersection over Union)
        preds_bin = (preds > 0.5).float()
        intersection = (preds_bin * masks).sum()
        union = preds_bin.sum() + masks.sum() - intersection
        iou = intersection / (union + 1e-6)
        
        self.log("val_loss", loss, prog_bar=True)
        self.log("val_iou", iou, prog_bar=True)
        return loss
        
    def configure_optimizers(self):
        return torch.optim.AdamW(self.parameters(), lr=self.hparams.lr)

if __name__ == "__main__":
    model = ShadowLitterModel()
    print("ShadowLitterModel (Prithvi-Backbone) initialized.")
