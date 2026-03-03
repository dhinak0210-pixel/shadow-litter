import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class PlanetTaskingLogic:
    """
    Simulation of PlanetScope and SkySat Emergency Tasking Workflows.
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.task_registry = "reports/active_tasks.json"
        os.makedirs("reports", exist_ok=True)
        if not os.path.exists(self.task_registry):
            with open(self.task_registry, 'w') as f:
                json.dump([], f)

    def trigger_tasking(self, site_id: str, location: List[float], weight_kg: float):
        """
        Determines and tasks the appropriate satellite based on reported weight.
        """
        timestamp = datetime.now().isoformat()
        task_details = {
            "site_id": site_id,
            "location": location,
            "weight": weight_kg,
            "timestamp": timestamp,
            "status": "INITIALIZING"
        }

        if weight_kg > 500:
            task_details["satellite"] = "SkySat-0.8m"
            task_details["priority"] = "EMERGENCY"
            task_details["eta_hours"] = 4
            task_details["label"] = "SkySat High-Res Rapid Tasking"
            print(f"🚨 CRITICAL WEIGHT: {weight_kg}kg. Tasking SkySat for 0.8m resolution overpass...")
        elif weight_kg > 100:
            task_details["satellite"] = "PlanetScope-3.7m"
            task_details["priority"] = "HIGH"
            task_details["eta_hours"] = 24
            task_details["label"] = "PlanetScope Daily Refresh"
            print(f"⚠️ HEAVY DUMPING: {weight_kg}kg. Tasking next PlanetScope overpass...")
        else:
            return None

        # Simulate API Request to Planet
        task_details["task_id"] = f"PLN-TASK-{int(time.time())}"
        task_details["status"] = "ACTIVE_TASKED"
        
        self._register_task(task_details)
        return task_details

    def _register_task(self, task):
        with open(self.task_registry, 'r') as f:
            tasks = json.load(f)
        tasks.append(task)
        # Keep only last 10 tasks for demo
        tasks = tasks[-10:]
        with open(self.task_registry, 'w') as f:
            json.dump(tasks, f, indent=2)

    def process_and_publish(self, task_id: str):
        """
        Simulates the download and processing cycle.
        In reality, this would poll Planet's Orders API.
        """
        # Mocking instantaneous "auto-processing" for the dashboard
        with open(self.task_registry, 'r') as f:
            tasks = json.load(f)
        
        for t in tasks:
            if t["task_id"] == task_id:
                t["status"] = "PROCESSED"
                t["map_label"] = "Emergency Verification"
                t["image_url"] = "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5d/Illegal_garbage_dump.jpg/320px-Illegal_garbage_dump.jpg" if t["weight"] < 500 else "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Waste_Management_1_bg_043004.jpg/320px-Waste_Management_1_bg_043004.jpg"
        
        with open(self.task_registry, 'w') as f:
            json.dump(tasks, f, indent=2)

if __name__ == "__main__":
    tasker = PlanetTaskingLogic(api_key="SIMULATED_PLANET_KEY")
    
    # CASE 1: 120kg Load
    print("\n--- Processing Report: Site SM-09 ---")
    tasker.trigger_tasking("SM-09", [9.918, 78.108], 120.0)
    
    # CASE 2: 750kg Load
    print("\n--- Processing Report: Site SM-14 ---")
    task = tasker.trigger_tasking("SM-14", [9.935, 78.130], 750.0)
    if task:
        tasker.process_and_publish(task["task_id"])
    
    print("\nTasking Log updated in reports/active_tasks.json")
