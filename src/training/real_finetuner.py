"""
Fine-tuning entry point for Shadow Litter.
Trains the NASA Prithvi model on your local Madurai annotations.
"""
import pytorch_lightning as pl
from torch.utils.data import DataLoader
from src.training.geospatial_dataset import ShadowLitterDataset
from src.models.real_model_core import ShadowLitterModel
import os

def run_fine_tuning(image_dir: str, labels_json: str):
    # 1. Setup Data
    dataset = ShadowLitterDataset(image_dir, labels_json)
    train_loader = DataLoader(dataset, batch_size=4, shuffle=True, num_workers=2)
    
    # 2. Setup Model
    model = ShadowLitterModel(lr=5e-5)
    
    # 3. Setup Trainer
    trainer = pl.Trainer(
        max_epochs=20,
        accelerator="auto", # Uses GPU if available
        devices=1,
        precision="16-mixed", # Efficient training
        default_root_dir="models/checkpoints"
    )
    
    print("🚀 Starting fine-tuning on real Madurai labels...")
    trainer.fit(model, train_loader)
    
    # 4. Save final weight
    os.makedirs("weights", exist_ok=True)
    trainer.save_checkpoint("weights/shadow_litter_prithvi_v1.ckpt")
    print("✅ Model saved to weights/shadow_litter_prithvi_v1.ckpt")

if __name__ == "__main__":
    # Example paths
    IMAGE_PATH = "data/processed"
    LABELS_PATH = "data/annotations/labels.json"
    
    if os.path.exists(LABELS_PATH):
        run_fine_tuning(IMAGE_PATH, LABELS_PATH)
    else:
        print(f"❌ Error: {LABELS_PATH} not found. Did you run the annotation tool first?")
