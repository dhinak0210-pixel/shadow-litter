"""
Dataset class for training on real satellite images and COCO annotations.
Handles spectral channel alignment and spatial augmentation.
"""
import torch
import numpy as np
import rasterio
from torch.utils.data import Dataset
from pathlib import Path
from pycocotools.coco import COCO
import cv2

class ShadowLitterDataset(Dataset):
    """
    Reads TIFF imagery and corresponding COCO annotations.
    """
    
    def __init__(self, image_dir: str, annotation_file: str, transform=None):
        self.image_dir = Path(image_dir)
        self.coco = COCO(annotation_file)
        self.ids = list(self.coco.imgs.keys())
        self.transform = transform
        
    def __len__(self):
        return len(self.ids)
        
    def __getitem__(self, index):
        img_id = self.ids[index]
        ann_ids = self.coco.getAnnIds(imgIds=img_id)
        anns = self.coco.loadAnns(ann_ids)
        
        path = self.image_dir / self.coco.loadImgs(img_id)[0]['file_name']
        
        # Load 4-band image (Red, Green, Blue, NIR)
        with rasterio.open(path) as src:
            image = src.read().astype(np.float32)
            # Prithvi expects 6 bands, we repeat/pad if necessary or use the native 4
            # For this MVP, we stack Blue, Green, Red, NIR, Edge1, Edge2
            # B02 (Blue), B03 (Green), B04 (Red), B08 (NIR)
            # We pad with zeros or copies for the remaining 2 bands to satisfy Prithvi
            if image.shape[0] < 6:
                padding = np.zeros((6 - image.shape[0], image.shape[1], image.shape[2]), dtype=np.float32)
                image = np.concatenate([image, padding], axis=0)
        
        # Create Binary Mask from COCO polygons
        mask = np.zeros((image.shape[1], image.shape[2]), dtype=np.float32)
        for ann in anns:
            if 'segmentation' in ann:
                # coco.annToMask handles polygon conversion
                mask = np.maximum(mask, self.coco.annToMask(ann))
        
        # Convert to tensor (C, H, W)
        image = torch.from_numpy(image)
        mask = torch.from_numpy(mask).unsqueeze(0)
        
        # For Prithvi, we need (C, T, H, W). We use T=1 for single-time detection
        image = image.unsqueeze(1) # (6, 1, H, W)
        
        if self.transform:
            image, mask = self.transform(image, mask)
            
        return image, mask

if __name__ == "__main__":
    # Example validation logic
    print("ShadowLitterDataset initialized (Logic Check)")
