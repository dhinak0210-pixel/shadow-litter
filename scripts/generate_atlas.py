"""
scripts/generate_atlas.py
──────────────────────────
Madurai Waste Atlas — Automated PDF/Image high-res map generator.
Combines AI detections into a presentation-quality visual for city officials.
"""
from __future__ import annotations
import matplotlib.pyplot as plt
from datetime import date
from pathlib import Path
from src.agent.database import DumpArchive

def generate_report():
    print("Generating Madurai Waste Atlas...")
    archive = DumpArchive()
    dumps = archive.query_history(limit=500)
    
    if not dumps:
        print("No detections in database to map.")
        return

    # Create visual
    fig, ax = plt.subplots(figsize=(10, 10), facecolor='#0d1117')
    ax.set_facecolor('#0d1117')
    
    lats = [d['lat'] for d in dumps]
    lons = [d['lon'] for d in dumps]
    areas = [d['area_sqm'] / 10 for d in dumps]
    
    # Heatmap dots
    scatter = ax.scatter(lons, lats, s=areas, c=lats, cmap='YlOrRd', 
                        alpha=0.6, edgecolors='white', linewidth=0.5)
    
    # Label top 3 largest
    sorted_dumps = sorted(dumps, key=lambda x: x['area_sqm'], reverse=True)
    for d in sorted_dumps[:3]:
        ax.annotate(f"{d['zone'].replace('_',' ').title()}\n({d['area_sqm']:.0f}m²)",
                   (d['lon'], d['lat']), color='white', fontsize=8,
                   xytext=(5, 5), textcoords='offset points',
                   bbox=dict(boxstyle='round,pad=0.3', fc='#1e3a5f', alpha=0.8))

    ax.set_title(f"shadow-litter :: MADURAI WASTE ATLAS\nOrbital Intelligence Summary - {date.today().isoformat()}", 
                color='white', fontsize=14, pad=20)
    ax.grid(True, color='#1e3a5f', alpha=0.3)
    ax.tick_params(colors='white')
    
    for spine in ax.spines.values():
        spine.set_edgecolor('#1e3a5f')

    out_path = Path("deliverables/madurai_waste_atlas.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
    print(f"✅ Atlas generated → {out_path}")
    archive.close()

if __name__ == "__main__":
    generate_report()
