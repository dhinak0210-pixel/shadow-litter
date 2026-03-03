"""
Script to download real Sentinel-2 data for Madurai over a given time range.
"""
import os
import yaml
from datetime import datetime, timedelta
from src.auth.copernicus_auth import ESAAuthenticator, CopernicusCredentials
from src.data.real_sentinel_api import CopernicusDataSpaceAPI

def acquire_real_data():
    # Load config
    with open("configs/default.yaml") as f:
        config = yaml.safe_load(f)
    
    creds = CopernicusCredentials(
        username=config['copernicus_user'],
        password=config['copernicus_pass']
    )
    auth = ESAAuthenticator(creds)
    api = CopernicusDataSpaceAPI(auth)
    
    # Madurai Bounds
    footprint = "POLYGON((78.0 9.8, 78.3 9.8, 78.3 10.1, 78.0 10.1, 78.0 9.8))"
    
    print("Searching for recent clear imagery of Madurai...")
    products = api.search_products(
        footprint_wkt=footprint,
        start_date=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
        end_date=datetime.now().strftime("%Y-%m-%d"),
        cloud_cover_lt=10.0,
        top=2
    )
    
    if not products:
        print("No clear imagery found in the last 30 days. Expanding search to last 90 days...")
        products = api.search_products(
            footprint_wkt=footprint,
            start_date=(datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
            end_date=datetime.now().strftime("%Y-%m-%d"),
            cloud_cover_lt=15.0,
            top=2
        )

    if products:
        for product in products:
            product_id = product['Id']
            product_name = product['Name']
            target_path = f"data/raw/{product_name}.zip"
            
            os.makedirs("data/raw", exist_ok=True)
            
            print(f"Found: {product_name} (ID: {product_id})")
            print(f"Starting download to {target_path}...")
            
            # Real download call
            try:
                api.download_product(product_id, target_path)
                print(f"✅ Successfully downloaded {product_name}")
            except Exception as e:
                print(f"❌ Download failed for {product_name}: {e}")
                print("TIP: Ensure your credentials in configs/default.yaml or env vars (COPERNICUS_USER, COPERNICUS_PASS) are correct.")
    else:
        print("No suitable products found.")

if __name__ == "__main__":
    acquire_real_data()
