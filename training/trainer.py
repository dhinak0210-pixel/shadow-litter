import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingWarmRestarts
import pytorch_lightning as pl
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping
from models.siamese_unet import SiameseUNet

class ChangeDetectionLoss(nn.Module):
    """
    Combined BCE + Dice loss for imbalanced change detection.
    """
    
    def __init__(self, bce_weight=0.5, dice_weight=0.5):
        super().__init__()
        self.bce = nn.BCELoss()
        self.bce_weight = bce_weight
        self.dice_weight = dice_weight
        
    def dice_loss(self, pred, target, smooth=1.0):
        pred = pred.contiguous()
        target = target.contiguous()
        intersection = (pred * target).sum(dim=2).sum(dim=2)
        loss = (1 - ((2. * intersection + smooth) / 
                     (pred.sum(dim=2).sum(dim=2) + target.sum(dim=2).sum(dim=2) + smooth)))
        return loss.mean()
    
    def forward(self, pred, target):
        bce = self.bce(pred, target)
        dice = self.dice_loss(pred, target)
        return self.bce_weight * bce + self.dice_weight * dice

class ShadowLitterModel(pl.LightningModule):
    def __init__(self, learning_rate=1e-4):
        super().__init__()
        self.model = SiameseUNet(n_channels=3, n_classes=1)
        self.criterion = ChangeDetectionLoss()
        self.learning_rate = learning_rate
        self.save_hyperparameters()
        
    def forward(self, x1, x2):
        return self.model(x1, x2)
    
    def training_step(self, batch, batch_idx):
        before, after, mask = batch
        pred = self(before, after)
        loss = self.criterion(pred, mask)
        self.log('train_loss', loss)
        return loss
    
    def validation_step(self, batch, batch_idx):
        before, after, mask = batch
        pred = self(before, after)
        loss = self.criterion(pred, mask)
        
        # Calculate IoU
        pred_binary = (pred > 0.5).float()
        intersection = (pred_binary * mask).sum()
        union = (pred_binary + mask).clamp(0, 1).sum()
        iou = intersection / (union + 1e-8)
        
        self.log('val_loss', loss)
        self.log('val_iou', iou)
        return loss
    
    def configure_optimizers(self):
        optimizer = AdamW(self.parameters(), lr=self.learning_rate, weight_decay=0.01)
        scheduler = CosineAnnealingWarmRestarts(optimizer, T_0=10, T_mult=2)
        return [optimizer], [scheduler]

# Training execution
def train_model():
    from pytorch_lightning import Trainer
    from training.dataset import ShadowLitterDataset, collect_real_backgrounds
    from torch.utils.data import DataLoader
    
    print("Step 1: Preparing Dataset...")
    real_bgs = collect_real_backgrounds(n_patches=100)
    
    train_ds = ShadowLitterDataset(background_patches=real_bgs, n_samples=2000)
    val_ds = ShadowLitterDataset(background_patches=real_bgs, n_samples=200)
    
    train_loader = DataLoader(train_ds, batch_size=8, shuffle=True, num_workers=4)
    val_loader = DataLoader(val_ds, batch_size=8, shuffle=False, num_workers=4)
    
    print("Step 2: Initializing Model...")
    model = ShadowLitterModel()
    
    # Callbacks
    checkpoint_callback = ModelCheckpoint(
        monitor='val_iou',
        mode='max',
        save_top_k=3,
        filename='shadow-litter-{epoch:02d}-{val_iou:.3f}'
    )
    
    early_stop = EarlyStopping(monitor='val_iou', patience=15, mode='max')
    
    # Trainer
    trainer = Trainer(
        max_epochs=50,
        accelerator='gpu' if torch.cuda.is_available() else 'cpu',
        devices=1,
        callbacks=[checkpoint_callback, early_stop],
        precision=16 if torch.cuda.is_available() else 32,
        gradient_clip_val=1.0
    )
    
    print("Step 3: Starting Training...")
    trainer.fit(model, train_dataloaders=train_loader, val_dataloaders=val_loader)
    
    return trainer, model

if __name__ == "__main__":
    train_model()
