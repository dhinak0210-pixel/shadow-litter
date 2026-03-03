import os
from typing import Dict, List
import json
from datetime import datetime

class shadow_litter_notifier:
    """
    Multi-channel alert system for Shadow Litter.
    Handles WhatsApp (via Twilio/Mock), Email, and Civic Dashboard push.
    """
    
    def __init__(self, config_path: str = "config/notifications.json"):
        self.log_file = "reports/notification_log.json"
        os.makedirs("reports", exist_ok=True)
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {"whatsapp_enabled": False, "email_enabled": False}
            
    def alert_stakeholders(self, detection: Dict):
        """
        Dispatches alerts based on priority and ward location.
        """
        priority = detection.get('priority', 'MEDIUM')
        ward = detection.get('ward', 'Unknown')
        area = detection.get('area_sqm', 0)
        
        message = f"🚨 SHADOW LITTER ALERT: New dump site detected in {ward}. Area: {area:.0f}sqm. Priority: {priority}."
        
        # 1. Log to persistent registry
        self._log_notification(detection, message)
        
        # 2. WhatsApp Alert (Mocked for Demo)
        if priority == 'HIGH':
            print(f"[WHATSAPP PUSH] To: Ward_{ward}_Assoc | Msg: {message}")
            
        # 3. Notification to Municipal App
        print(f"[CIVIC PUSH] To: Madurai_Corp_API | Msg: {message}")

    def _log_notification(self, detection: Dict, message: str):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "ward": detection.get('ward'),
            "area": detection.get('area_sqm'),
            "priority": detection.get('priority'),
            "message": message,
            "coordinates": str(detection.get('centroid'))
        }
        
        logs = []
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                try:
                    logs = json.load(f)
                except:
                    logs = []
                    
        logs.append(log_entry)
        with open(self.log_file, 'w') as f:
            json.dump(logs, f, indent=4)

if __name__ == "__main__":
    # Test notification
    notifier = shadow_litter_notifier()
    test_detection = {
        "ward": "Thathaneri",
        "area_sqm": 450.5,
        "priority": "HIGH",
        "centroid": (9.93, 78.11)
    }
    notifier.alert_stakeholders(test_detection)
