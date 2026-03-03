import os
import sys
import torch

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.siamese_unet import SiameseUNet

def test_model():
    print("Initializing SiameseUNet...")
    model = SiameseUNet(n_channels=3, n_classes=1)
    
    # Create dummy batch [B, C, H, W]
    print("Creating dummy input tensors (Before and After)...")
    batch_size = 2
    x1 = torch.randn(batch_size, 3, 256, 256)
    x2 = torch.randn(batch_size, 3, 256, 256)
    
    print("Running forward pass...")
    try:
        with torch.no_grad():
            output = model(x1, x2)
            
        print("\nSuccess!")
        print(f"Output Shape: {output.shape} \t Expected: ({batch_size}, 1, 256, 256)")
        
        # Test bounds of sigmoid output
        min_val, max_val = output.min().item(), output.max().item()
        print(f"Output range: [{min_val:.4f}, {max_val:.4f}] \t Expected: [0, 1]")
        
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"Total Trainable Parameters: {total_params:,}")
            
    except Exception as e:
        print(f"Error occurred during forward pass: {e}")

if __name__ == "__main__":
    test_model()
