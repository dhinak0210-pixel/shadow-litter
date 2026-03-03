"""
Satellite-aware preprocessing for Sentinel-2 data.
Handles atmospheric correction scaling and NIR fusion.
"""
import rasterio
import numpy as np
from pathlib import Path

def preprocess_sentinel_tile(tile_path: str, output_dir: str):
    """
    Scale 16-bit TOA reflectance to 0-1 and extract RGB + NIR.
    """
    output_path = Path(output_dir) / Path(tile_path).name.replace(".tif", "_preprocessed.tif")
    
    with rasterio.open(tile_path) as src:
        # Sentinel-2 Bands: Blue(2), Green(3), Red(4), NIR(8)
        # Assuming input is a stacked TIFF or SAFE format
        # Mapping for this specific project: [Red, Green, Blue, NIR]
        data = src.read([1, 2, 3, 4]) 
        
        # Scale to 0.0 - 1.0 (Sentinel-2 typically 0-10000 range)
        data = data.astype(np.float32) / 10000.0
        data = np.clip(data, 0, 1)
        
        # Update profile for float32
        profile = src.profile
        profile.update(dtype=rasterio.float32, count=4)
        
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(data)
            
    print(f"✅ Preprocessed {tile_path} -> {output_path}")
    return str(output_path)

if __name__ == "__main__":
    # Example usage
    # preprocess_sentinel_tile("data/raw/sample.tif", "data/processed")
    pass
