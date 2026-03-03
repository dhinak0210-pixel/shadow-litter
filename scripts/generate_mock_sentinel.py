"""
Generates a mock 4-band Sentinel-2 GeoTIFF for pipeline testing.
Bands: Red, Green, Blue, NIR.
"""
import numpy as np
import rasterio
from rasterio.transform import from_origin
import os

def generate_mock_tile(output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 512x512 tile, 4 bands
    # Values as 16-bit uint (0-10000 range)
    width, height = 512, 512
    data = np.random.randint(0, 3000, size=(4, height, width), dtype=np.uint16)
    
    # Add a "dump" like feature (bright in RGB, dark in NIR)
    # Patch at 100, 100
    data[0:3, 100:150, 100:150] = 8000 # Bright Red/Green/Blue
    data[3, 100:150, 100:150] = 500   # Dark NIR (non-vegetated)
    
    # Simple transform around Madurai
    transform = from_origin(78.12, 9.92, 0.0001, 0.0001)
    
    new_dataset = rasterio.open(
        output_path,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=4,
        dtype=data.dtype,
        crs='+proj=latlong',
        transform=transform,
    )
    
    new_dataset.write(data)
    new_dataset.close()
    print(f"✅ Generated Mock Sentinel Tile: {output_path}")

if __name__ == "__main__":
    generate_mock_tile("data/raw/mock_madurai_tile.tif")
