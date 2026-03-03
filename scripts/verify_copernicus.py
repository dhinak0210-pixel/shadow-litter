"""
Script to verify Copernicus Authentication and OData API.
"""
import os
import yaml
from src.auth.copernicus_auth import ESAAuthenticator, CopernicusCredentials
from src.data.real_sentinel_api import CopernicusDataSpaceAPI

def verify():
    # Load config
    with open("configs/default.yaml") as f:
        config = yaml.safe_load(f)
    
    print(f"Verifying credentials for: {config['copernicus_user']}")
    
    creds = CopernicusCredentials(
        username=config['copernicus_user'],
        password=config['copernicus_pass']
    )
    auth = ESAAuthenticator(creds)
    
    try:
        token = auth.authenticate()
        print("✅ Authentication successful!")
        
        api = CopernicusDataSpaceAPI(auth)
        # Test search over Madurai North
        footprint = "POLYGON((78.12 9.92, 78.16 9.92, 78.16 9.96, 78.12 9.96, 78.12 9.92))"
        products = api.search_products(footprint, top=1)
        
        if products:
            print(f"✅ API Search successful! Found product: {products[0]['Name']}")
        else:
            print("⚠️ Authentication worked but no products found for this area/date.")
            
    except Exception as e:
        print(f"❌ Error during verification: {e}")

if __name__ == "__main__":
    verify()
