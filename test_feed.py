import os
import sys

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_engine.sentinel_hub import SentinelFeed
from datetime import datetime, timedelta

def test_feed():
    print("Initializing SentinelFeed...")
    feed = SentinelFeed()
    
    # Define a recent date range (last 30 days)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    start_date_str = start_date.isoformat() + "Z"
    end_date_str = end_date.isoformat() + "Z"
    
    print(f"Searching for clear imagery between {start_date_str} and {end_date_str}...")
    
    # Search for stack
    try:
        scenes = feed.search_temporal_stack(start_date_str, end_date_str, cloud_cover=20.0)
        
        if not scenes:
            print("No scenes found matching the criteria.")
            return
            
        print(f"Found {len(scenes)} scenes!")
        for i, scene in enumerate(scenes[:3]):  # Just print first 3
            print(f"Scene {i+1}: ID={scene['id']}, Date={scene['datetime']}, Cloud Cover={scene['cloud_cover']}%")
            
        print("\nAttempting to download B04 (Red), B08 (NIR), and B11 (SWIR) for the clearest scene...")
        
        # Sort by cloud cover and get the best one
        best_scene = sorted(scenes, key=lambda x: x['cloud_cover'])[0]
        print(f"Selected Scene: {best_scene['id']} with {best_scene['cloud_cover']}% cloud cover")
        print("Available assets:", list(best_scene['assets'].keys()))
        
        # Download
        bands = feed.download_bands(best_scene, ['B04', 'B08', 'B11'])
        print(f"Successfully downloaded bands! Shape: {bands.shape}, Dtype: {bands.dtype}")
        
    except Exception as e:
        print(f"Error occurred during Feed testing: {e}")

if __name__ == "__main__":
    test_feed()
