import os
import sys
import torch

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent.core_agent import ShadowLitterAgent

def run_manual_scan():
    print("Initializing ShadowLitterAgent for manual ritual...")
    # Using dummy weights since training is still ongoing
    agent = ShadowLitterAgent(
        model_path="weights/shadow-litter-best.ckpt",
        config_path="config/madurai.json"
    )
    
    print("Executing Weekly Scan Ritual (Synchronous Test)...")
    try:
        # We call it as a normal method. 
        # Note: In the core_agent.py, it's defined as a method but decorated as a task.
        # Calling it directly as agent.weekly_scan_ritual() will work as a normal method if celery isn't active.
        result = agent.weekly_scan_ritual()
        print(f"\nRitual Result: {result}")
        
        # Check if reports were generated
        reports = os.listdir('reports') if os.path.exists('reports') else []
        if any('madurai_corp_' in r for r in reports):
            print(f"Success! Reports generated in 'reports/' directory: {reports}")
        else:
            print("Warning: No reports were generated. Check for data availability or cloud cover.")
            
    except Exception as e:
        print(f"Error during manual scan ritual: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_manual_scan()
