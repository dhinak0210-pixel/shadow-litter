import os
import sys
import numpy as np
import torch

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from training.synthetic_generator import DumpSynthesizer

def test_synthesizer():
    print("Initializing DumpSynthesizer...")
    synth = DumpSynthesizer(image_size=256)
    
    # Create a dummy clean image (mocking satellite imagery with shape [H, W, 3])
    # Values somewhat representing satellite surface reflectances (0-255 scaled)
    print("Generating a dummy clean satellite patch...")
    clean_image = np.random.uniform(50, 150, (256, 256, 3)).astype(np.float32)
    
    print("Synthesizing dump pair...")
    try:
        before_aug, after_aug, mask = synth.synthesize_pair(clean_image)
        
        print("\nSuccess!")
        print(f"Before Image Shape: {before_aug.shape} Type: {type(before_aug)}")
        print(f"After Image Shape: {after_aug.shape} Type: {type(after_aug)}")
        print(f"Mask Shape: {mask.shape} Type: {type(mask)}")
        
        # Check if mask actually has positive values
        if mask.sum() > 0:
            print("Mask successfully generated waste pixels.")
        else:
            print("Warning: Mask is entirely empty.")
            
    except Exception as e:
        print(f"Error occurred during synthesizing: {e}")

if __name__ == "__main__":
    test_synthesizer()
