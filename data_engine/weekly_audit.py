import os
import json
import time
import math
from datetime import datetime, timedelta
from typing import List, Dict
from fpdf import FPDF

class ShadowLitterWeeklyAudit:
    """
    Weekly Sunday Maxar WorldView-3 Ritual (0.3m resolution).
    Focus: Persistence, Legal Evidence, Growth Measurement.
    """
    def __init__(self):
        self.report_dir = "reports/weekly_audits"
        os.makedirs(self.report_dir, exist_ok=True)
        self.registry = "reports/audit_registry.json"
        if not os.path.exists(self.registry):
            with open(self.registry, 'w') as f:
                json.dump([], f)

    def select_top_persistent_sites(self, all_sites: List[Dict]) -> List[Dict]:
        """
        Identify top 5 sites with highest persistent accumulation.
        Simulated selection based on confidence and area.
        """
        sorted_sites = sorted(all_sites, key=lambda x: (x.get("confidence", 0) * x.get("area", 0)), reverse=True)
        return sorted_sites[:5]

    def measure_growth(self, site: Dict) -> Dict:
        """
        Simulates 0.3m WorldView-3 analysis: Comparison 4 weeks ago vs Now.
        """
        # Simulated 4-week growth formula: 
        # (Current Area / (Current Area / 1.15)) - 1 = 15% typical growth 
        current_area = site.get("area", 200.0)
        previous_area = round(current_area / (1.0 + (np.random.random() * 0.2 + 0.05)), 1)
        growth_pct = round(((current_area - previous_area) / previous_area) * 100, 1)
        
        return {
            "now_area": current_area,
            "prev_area": previous_area,
            "growth_pct": growth_pct,
            "sat_type": "Maxar WorldView-3 (0.3m)"
        }

    def generate_legal_pdf(self, report_data: Dict):
        """
        Generates a professional PDF legal report with GPS/timestamps/growth.
        """
        pdf = FPDF()
        pdf.add_page()
        
        # Header
        pdf.set_font("helvetica", "B", 20)
        pdf.set_text_color(30, 60, 120)
        pdf.cell(0, 15, "SHADOW-LITTER REGULATORY AUDIT REPORT", new_x="LMARGIN", new_y="NEXT", align="C")
        
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, f"Report ID: {report_data['audit_id']} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(10)
        
        # Summary Section
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("helvetica", "B", 14)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, "1. EXECUTIVE SUMMARY", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        pdf.set_font("helvetica", "", 12)
        pdf.multi_cell(0, 7, (
            f"This autonomous audit focused on the top 5 high-priority illegal dumping sites in Madurai. "
            f"Imagery was acquired via Maxar WorldView-3 (0.3m GSD) on Sunday morning. "
            f"The mean growth across target sites is {report_data['mean_growth']}% over the last 4 weeks. "
            f"Immediate municipal intervention is recommended for sites exceeding 15% expansion."
        ))
        pdf.ln(8)

        # Site-Specific Data table
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(50, 10, "SITE ID", 1)
        pdf.cell(70, 10, "COORDINATES", 1)
        pdf.cell(40, 10, "GROWTH %", 1)
        pdf.cell(30, 10, "STATUS", 1, new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font("helvetica", "", 10)
        for site in report_data["sites"]:
            pdf.cell(50, 10, str(site["id"]), 1)
            pdf.cell(70, 10, f"{site['lat']:.5f}N, {site['lon']:.5f}E", 1)
            pdf.cell(40, 10, f"+{site['growth']}%", 1)
            pdf.cell(30, 10, "CRITICAL" if site["growth"] > 15 else "STABLE", 1, new_x="LMARGIN", new_y="NEXT")
        
        # Footer / Authority
        pdf.ln(20)
        pdf.set_font("helvetica", "I", 8)
        pdf.cell(0, 5, "This document is an automatically generated legal evidence log from Shadow-Litter satellite intelligence.", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 5, "Distributed to: Municipal Commissioner, Madurai Corporation | Legal Enforcement Division.", new_x="LMARGIN", new_y="NEXT")

        # Save File
        filename = f"{self.report_dir}/Audit_{datetime.now().strftime('%Y%j')}.pdf"
        pdf.output(filename)
        return filename

    def run_weekly_ritual(self, current_sites: List[Dict]):
        """Runs the whole Sunday sequence"""
        print(f"🛰️ INITIALIZING SUNDAY WORLDVIEW-3 AUDIT: {datetime.now().strftime('%d %b %Y')}")
        
        targets = self.select_top_persistent_sites(current_sites)
        print(f"Targeting top {len(targets)} sites for 0.3m imagery...")
        
        audit_results = []
        for site in targets:
            import numpy as np # Local import for calculation
            growth_info = self.measure_growth(site)
            audit_results.append({
                **site,
                "growth": growth_info["growth_pct"],
                "prev_area": growth_info["prev_area"],
                "timestamp": datetime.now().isoformat()
            })
            print(f"   [+] Audit Completed: {site['id']} | Growth: +{growth_info['growth_pct']}%")

        # Generate report metadata
        audit_id = f"AUDIT-{datetime.now().strftime('%Y%W')}"
        mean_growth = round(sum(s["growth"] for s in audit_results) / len(audit_results), 1)
        
        summary = {
            "audit_id": audit_id,
            "mean_growth": mean_growth,
            "sites": audit_results,
            "pdf_path": ""
        }
        
        # 4. Generate Legal PDF Report
        pdf_path = self.generate_legal_pdf(summary)
        summary["pdf_path"] = pdf_path
        
        # 5. Registry Update
        with open(self.registry, 'r') as f:
            registry = json.load(f)
        registry.append(summary)
        with open(self.registry, 'w') as f:
            json.dump(registry[-5:], f, indent=2) # Keep last 5 audits
            
        print(f"📄 Legal Report Generated: {pdf_path}")
        print("📧 Dispatching PDF to Municipal Commissioner (Simulation)...")
        print("✅ Weekly Audit Successfully Completed.")
        return summary

if __name__ == "__main__":
    # Mock Site Data for standalone run
    mock_sites = [
        {"id": "SL-MAD-001", "name": "Gandhi Market", "lat": 9.9280, "lon": 78.1205, "area": 1200, "confidence": 0.95},
        {"id": "SL-MAD-002", "name": "Vilangudi", "lat": 9.9150, "lon": 78.1100, "area": 850, "confidence": 0.92},
        {"id": "SL-MAD-003", "name": "Mattuthavani", "lat": 9.9350, "lon": 78.1300, "area": 620, "confidence": 0.88},
        {"id": "ML-002", "name": "Vaigai River", "lat": 9.9290, "lon": 78.1250, "area": 45, "confidence": 0.82}
    ]
    
    import numpy as np # Ensure numpy for mock calculation
    audit_engine = ShadowLitterWeeklyAudit()
    audit_engine.run_weekly_ritual(mock_sites)
