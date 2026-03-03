"""
Script to initialize Google Earth Engine.
"""
import ee
import os

def init_gee():
    print("Starting Google Earth Engine Initialization...")
    try:
        # This will open a browser window for authentication if not already authenticated
        ee.Authenticate()
        ee.Initialize(project='your-project-id') # Replace with your GCP project ID
        print("✅ GEE Initialized successfully!")
        
        # Test query
        image = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").first()
        info = image.getInfo()
        print(f"✅ Successfully fetched test image: {info['id']}")
        
    except Exception as e:
        print(f"❌ GEE Initialization failed: {e}")
        print("\nTIP: Make sure you have a Google Cloud Project with Earth Engine API enabled.")

if __name__ == "__main__":
    init_gee()
