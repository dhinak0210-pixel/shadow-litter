import torch
import numpy as np
from typing import Tuple
import albumentations as A
from albumentations.pytorch import ToTensorV2

class DumpSynthesizer:
    """
    Generates synthetic waste dumps on clean satellite imagery.
    Creates training data without manual labeling.
    """
    
    def __init__(self, image_size=256):
        self.image_size = image_size
        self.augment = A.Compose([
            A.RandomRotate90(p=0.5),
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.5),
            A.Transpose(p=0.5),
            A.OneOf([
                A.MotionBlur(p=0.5),
                A.MedianBlur(blur_limit=3, p=0.5),
                A.GaussianBlur(blur_limit=3, p=0.5),
            ], p=0.3),
            A.ShiftScaleRotate(shift_limit=0.1, scale_limit=0.1, rotate_limit=15, p=0.5),
            A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ToTensorV2()
        ])
        
    def generate_dump_texture(self, size: Tuple[int, int]) -> np.ndarray:
        """
        Create realistic waste texture using Perlin noise + color distortion.
        Simulates spectral signature of garbage in RGB/NIR.
        """
        try:
            from noise import pnoise2
            has_noise = True
        except ImportError:
            has_noise = False
            
        height, width = size
        texture = np.zeros((height, width, 3), dtype=np.float32)
        
        scale = 100.0
        octaves = 6
        persistence = 0.5
        lacunarity = 2.0
        
        for i in range(height):
            for j in range(width):
                if has_noise:
                    noise_val = pnoise2(i/scale, j/scale, 
                                      octaves=octaves, 
                                      persistence=persistence, 
                                      lacunarity=lacunarity)
                else:
                    noise_val = np.random.uniform(-1, 1)
                
                # Map noise to garbage colors (grays, browns, whites)
                gray = 0.3 + 0.4 * noise_val
                texture[i, j] = [gray, gray * 0.9, gray * 0.85]
                
        return texture
    
    def synthesize_pair(self, clean_image: np.ndarray) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Create before/after pair with synthetic dump.
        Returns: before_tensor, after_tensor, mask_tensor
        """
        h, w = clean_image.shape[:2]
        
        # Before: clean image
        before = clean_image.copy()
        
        # After: add synthetic dump
        after = clean_image.copy()
        mask = np.zeros((h, w), dtype=np.float32)
        
        # Random dump parameters
        num_dumps = np.random.randint(1, 4)
        
        for _ in range(num_dumps):
            # Random ellipse parameters
            center_x = np.random.randint(w//4, 3*w//4)
            center_y = np.random.randint(h//4, 3*h//4)
            axis_a = np.random.randint(20, 60)
            axis_b = np.random.randint(15, 40)
            angle = np.random.randint(0, 180)
            
            # Generate texture
            texture = self.generate_dump_texture((axis_b*2, axis_a*2))
            
            # Create mask
            Y, X = np.ogrid[:h, :w]
            dist = ((X - center_x) * np.cos(np.radians(angle)) + 
                   (Y - center_y) * np.sin(np.radians(angle)))**2 / axis_a**2 + \
                   ((X - center_x) * np.sin(np.radians(angle)) - 
                   (Y - center_y) * np.cos(np.radians(angle)))**2 / axis_b**2
            
            dump_mask = (dist <= 1).astype(np.float32)
            
            # Blend texture with background
            try:
                roi = after[center_y-axis_b:center_y+axis_b, center_x-axis_a:center_x+axis_a]
                if roi.shape[:2] == texture.shape[:2]:
                    alpha = dump_mask[center_y-axis_b:center_y+axis_b, center_x-axis_a:center_x+axis_a]
                    alpha = np.stack([alpha]*3, axis=-1)
                    after[center_y-axis_b:center_y+axis_b, center_x-axis_a:center_x+axis_a] = \
                        roi * (1 - alpha * 0.7) + texture * alpha * 0.7
                        
                mask = np.maximum(mask, dump_mask)
            except Exception:
                pass
            
        # Apply augmentations
        before_aug = self.augment(image=before)['image']
        after_aug = self.augment(image=after)['image']
        
        return before_aug, after_aug, torch.from_numpy(mask).unsqueeze(0)
