import os
import time
import schedule
import subprocess

def job():
    print(f"[{time.ctime()}] Starting scheduled Weekly Scan Ritual...")
    try:
        # Run the manual scan script as a subprocess to simulate the agent action
        cmd = ["python", "run_manual_scan.py"]
        env = os.environ.copy()
        env["PYTHONPATH"] = env.get("PYTHONPATH", "") + ":."
        subprocess.run(cmd, env=env, check=True)
        print(f"[{time.ctime()}] Ritual complete.")
    except Exception as e:
        print(f"Error during scheduled ritual: {e}")

# Schedule for every Monday at 00:00
schedule.every().monday.at("00:00").do(job)

# For demo purposes, we'll also run it once now or every 10 minutes if we were in a long-running demo
# schedule.every(10).minutes.do(job)

print("Shadow Litter Scheduler Service Active.")
print("Monitoring for Monday 00:00 UTC pulses...")

while True:
    schedule.run_pending()
    time.sleep(60)
