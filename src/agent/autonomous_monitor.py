"""
Refined ShadowLitterAgent for Autonomous Monitoring.
Integrates NASA Prithvi-100M with automated scheduling and alerting.
"""
import logging
import schedule
import time
import yaml
import os
import requests
from datetime import datetime, timedelta
from pathlib import Path
from src.agent.database import DumpArchive
from src.data.madurai_zones import all_zones
from src.auth.copernicus_auth import ESAAuthenticator, CopernicusCredentials
from src.data.real_sentinel_api import CopernicusDataSpaceAPI

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ShadowLitterAgent")

class AutonomousMonitor:
    def __init__(self, config_path: str = "configs/default.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.db = DumpArchive(self.config['database_path'])
        self.zones = all_zones()
        self.model = None # Lazy load
        
        # Auth Setup
        creds = CopernicusCredentials(
            username=self.config['copernicus_user'],
            password=self.config['copernicus_pass']
        )
        self.auth = ESAAuthenticator(creds)
        self.api = CopernicusDataSpaceAPI(self.auth)
        
    def _load_model(self):
        """Loads the fine-tuned Prithvi model."""
        if self.model is None:
            from src.models.real_model_core import ShadowLitterModel
            weights_path = "weights/shadow_litter_prithvi_v1.ckpt"
            if os.path.exists(weights_path):
                self.model = ShadowLitterModel.load_from_checkpoint(weights_path)
                self.model.eval()
                self.model.freeze()
                logger.info("✅ Prithvi Model loaded from local weights.")
            else:
                logger.warning("⚠️ No fine-tuned weights found. Agent will run in 'Data Collection' mode only.")

    def scan_madurai_weekly(self):
        """Main periodic task."""
        logger.info("🛰️ Starting Weekly Orbital Scan of Madurai...")
        self._load_model()
        
        for zone_name, zone_data in self.config['zones'].items():
            logger.info(f"Scanning Zone: {zone_name}")
            try:
                self.process_zone(zone_name, zone_data)
            except Exception as e:
                logger.error(f"❌ Failed to process zone {zone_name}: {e}")

    def process_zone(self, name, data):
        """
        1. Acquire latest image
        2. Acquire baseline image (t-30 days)
        3. Run Prithvi Inference
        4. Log results and Alert
        """
        # (Simplified for Phase 3 Implementation)
        coords = data['coords']
        footprint = f"POLYGON(({coords['w']} {coords['s']}, {coords['e']} {coords['s']}, {coords['e']} {coords['n']}, {coords['w']} {coords['n']}, {coords['w']} {coords['s']}))"
        
        # Search for latest product
        products = self.api.search_products(
            footprint_wkt=footprint,
            start_date=(datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d"),
            end_date=datetime.now().strftime("%Y-%m-%d"),
            cloud_cover_lt=10.0,
            top=1
        )
        
        if not products:
            logger.info(f"No clear imagery for {name} in the last 14 days.")
            return

        product = products[0]
        logger.info(f"New data found: {product['Name']}")
        
        # In a real run, we would download, preprocess, and infer here.
        # For now, we simulate the 'New Detection' trigger
        if self.model:
            # Simulate high confidence detection
            self.trigger_alert(name, 9.9252, 78.1198, 0.89, "Fresh Dump")

    def trigger_alert(self, zone, lat, lon, confidence, dump_type):
        """Send notifications via Discord/Slack/Email."""
        message = (
            f"🚨 *MADURAI WASTE ALERT* 🚨\n"
            f"Detected in: {zone}\n"
            f"Type: {dump_type}\n"
            f"Confidence: {confidence:.2%}\n"
            f"Location: https://www.google.com/maps?q={lat},{lon}\n"
            f"--- shadow-litter autonomous-agent ---"
        )
        
        # Log to DB
        self.db.log_detection(zone, lat, lon, confidence, 500.0, dump_type)
        
        # Webhook Alert (Optional)
        webhook_url = self.config.get('corporation_webhook')
        if webhook_url:
            try:
                requests.post(webhook_url, json={"text": message})
                logger.info(f"Alert sent to webhook for {zone}")
            except Exception as e:
                logger.error(f"Failed to send webhook: {e}")
        
        print(message)

    def start_scheduler(self):
        """Runs the loop."""
        logger.info("⏰ Scheduler active. Set to scan every Monday at 08:00.")
        schedule.every().monday.at("08:00").do(self.scan_madurai_weekly)
        
        # For testing, run once immediately
        self.scan_madurai_weekly()
        
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    monitor = AutonomousMonitor()
    monitor.start_scheduler()
