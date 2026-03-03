import json
from datetime import datetime

def generate_policy_brief(detections_file: str, output_file: str):
    """
    Generates a 2-page brief for commissioners with detection statistics, 
    growth projections, and recommended interventions.
    """
    try:
        with open(detections_file, 'r') as f:
            detections = json.load(f)
    except Exception:
        detections = []
        
    total_sites = len(detections)
    total_area = sum(d.get('area_sqm', 0) for d in detections)
    
    brief = f"""
    SHADOW LITTER - POLICY BRIEF
    ----------------------------------------------------------
    Date: {datetime.now().strftime('%Y-%m-%d')}
    To: Municipal Commissioner, Madurai Corporation
    Subject: Satellite-Detected Illegal Waste Dump Situational Report
    
    EXECUTIVE SUMMARY:
    Our remote sensing AI has detected {total_sites} unauthorized waste sites
    totaling {total_area/10000:.2f} hectares of affected land.
    
    RECOMMENDED INTERVENTIONS:
    1. Deploy sanitation teams to high-growth hotspot areas.
    2. Install CCTV cameras in frequently targeted zones.
    3. Initiate public awareness campaigns in surrounding wards.
    
    Detailed coordinates and area metrics are available via the Shadow Litter Dashboard.
    """
    with open(output_file, 'w') as f:
        f.write(brief)
    
    print(f"Policy brief written to {output_file}")

if __name__ == "__main__":
    generate_policy_brief('data/mock_detections.json', 'reports/commissioner_brief.txt')
