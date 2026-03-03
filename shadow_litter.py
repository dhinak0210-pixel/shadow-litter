# shadow_litter.py — Single entry point
"""
Shadow Litter: Complete working system on real data.
Run: python shadow_litter.py --mode [train|infer|agent|dashboard]
"""

import argparse
import yaml
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Shadow Litter Satellite Intelligence")
    parser.add_argument('--mode', choices=['train', 'infer', 'agent', 'dashboard'], required=True)
    parser.add_argument('--config', default='configs/default.yaml')
    args = parser.parse_args()
    
    with open(args.config) as f:
        config = yaml.safe_load(f)
    
    if args.mode == 'train':
        from src.training.real_data_trainer import train_model
        train_model(config)
        
    elif args.mode == 'infer':
        from src.inference.production_inference import batch_process
        batch_process(config)
        
    elif args.mode == 'agent':
        from src.agent.autonomous_monitor import AutonomousShadowLitterAgent
        agent = AutonomousShadowLitterAgent(args.config)
        agent.run()
        
    elif args.mode == 'dashboard':
        from app.streamlit_dashboard import run_dashboard
        run_dashboard(config)

if __name__ == "__main__":
    main()
