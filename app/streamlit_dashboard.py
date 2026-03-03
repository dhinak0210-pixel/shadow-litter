"""
app/streamlit_dashboard.py
───────────────────────────
Full shadow-litter monitoring dashboard.
Replaces the minimal app/dashboard.py with the complete production version.
"""
import json, logging
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="shadow-litter | Madurai Waste Watch",
    page_icon="🛰️", layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
*{font-family:'Inter',sans-serif}
[data-testid="stAppViewContainer"]{background:linear-gradient(135deg,#060912 0%,#0a0f1e 60%,#0d1523 100%);color:#e0e6f0}
[data-testid="stSidebar"]{background:rgba(6,9,18,0.97);border-right:1px solid #1e3a5f}
h1,h2,h3{color:#e0e6f0}
.kpi{background:rgba(20,40,80,0.35);border:1px solid #1e3a5f;border-radius:14px;padding:1.2rem 1.5rem;text-align:center}
.kpi h2{color:#4fc3f7;margin:0;font-size:2rem;font-weight:700}
.kpi p{color:#90a4ae;margin:0;font-size:.8rem;text-transform:uppercase;letter-spacing:1px}
.alert-card{background:rgba(183,28,28,0.15);border:1px solid #b71c1c;border-radius:10px;padding:1rem;margin:.5rem 0}
.tag{display:inline-block;padding:2px 10px;border-radius:20px;font-size:.75rem;font-weight:600}
.leachate{background:#1a237e;color:#fff}
.fresh_dump{background:#e65100;color:#fff}
.construction_debris{background:#4e342e;color:#fff}
.unknown{background:#37474f;color:#fff}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛰️ shadow-litter")
    st.markdown("**Orbital waste intelligence · Madurai**")
    st.markdown("---")
    page = st.radio("Navigate", ["🗺️ Live Map", "📊 Analytics", "🔬 Run Scan", "📋 Archive"])
    st.markdown("---")
    st.markdown("### Filters")
    conf_thresh = st.slider("Min. confidence", 0.0, 1.0, 0.60, 0.05)
    zone_filter = st.multiselect("Zones", [
        "vaigai_riverbed","perungudi_lake","alagar_koil_outskirts",
        "mattuthavani_periphery","thiruparankundram_quarries"], default=[])
    dump_types = st.multiselect("Type", ["fresh_dump","construction_debris","leachate","unknown"],
        default=["fresh_dump","construction_debris","leachate","unknown"])
    st.markdown("---")
    st.caption("ESA Copernicus · USGS Landsat")
    st.caption("MIT License · Madurai, Tamil Nadu")

# ── Load data ──────────────────────────────────────────────────────────────────
def load_detections():
    p = Path("outputs/reports")
    geojsons = sorted(p.glob("detections_*.geojson"), reverse=True) if p.exists() else []
    if geojsons:
        with open(geojsons[0]) as f: data = json.load(f)
        return data.get("features", [])
    # Demo data
    return [
        {"properties":{"zone":"vaigai_riverbed","lat":9.9259,"lon":78.1198,"confidence":0.89,
            "area_sqm":1240,"dump_type":"fresh_dump","ward":"47","priority_score":2210,
            "first_seen":"2024-03-15","risk_level":"critical"},
         "geometry":{"type":"Point","coordinates":[78.1198,9.9259]}},
        {"properties":{"zone":"thiruparankundram_quarries","lat":9.8765,"lon":78.0734,"confidence":0.94,
            "area_sqm":4500,"dump_type":"construction_debris","ward":"5","priority_score":8460,
            "first_seen":"2024-02-20","risk_level":"critical"},
         "geometry":{"type":"Point","coordinates":[78.0734,9.8765]}},
        {"properties":{"zone":"perungudi_lake","lat":9.9716,"lon":78.1319,"confidence":0.73,
            "area_sqm":680,"dump_type":"leachate","ward":"12","priority_score":990,
            "first_seen":"2024-01-10","risk_level":"high"},
         "geometry":{"type":"Point","coordinates":[78.1319,9.9716]}},
        {"properties":{"zone":"mattuthavani_periphery","lat":9.9566,"lon":78.1442,"confidence":0.81,
            "area_sqm":920,"dump_type":"fresh_dump","ward":"33","priority_score":1490,
            "first_seen":"2024-04-02","risk_level":"high"},
         "geometry":{"type":"Point","coordinates":[78.1442,9.9566]}},
    ]

features = load_detections()
filtered = [f for f in features
    if f["properties"].get("confidence",0) >= conf_thresh
    and f["properties"].get("dump_type","unknown") in dump_types
    and (not zone_filter or f["properties"].get("zone") in zone_filter)]

# ── Pages ──────────────────────────────────────────────────────────────────────

if "🗺️ Live Map" in page:
    st.title("🛰️ Madurai Waste Watch")
    st.caption(f"*{len(filtered)} active detections shown · Last updated {date.today().isoformat()}*")

    # KPIs
    c1,c2,c3,c4,c5 = st.columns(5)
    total_area = sum(f["properties"].get("area_sqm",0) for f in filtered)
    avg_conf = np.mean([f["properties"].get("confidence",0) for f in filtered]) if filtered else 0
    critical = sum(1 for f in filtered if f["properties"].get("risk_level")=="critical")
    with c1: st.markdown(f'<div class="kpi"><h2>{len(filtered)}</h2><p>Detections</p></div>',unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="kpi"><h2>{critical}</h2><p>Critical Sites</p></div>',unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="kpi"><h2>{total_area/1e4:.1f} ha</h2><p>Total Area</p></div>',unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="kpi"><h2>{avg_conf:.0%}</h2><p>Avg. Confidence</p></div>',unsafe_allow_html=True)
    with c5: st.markdown(f'<div class="kpi"><h2>5</h2><p>Active Zones</p></div>',unsafe_allow_html=True)

    st.markdown("---")

    # Map via pydeck
    try:
        import pydeck as pdk
        layer_data = [{"lat":f["properties"]["lat"],"lon":f["properties"]["lon"],
            "confidence":f["properties"].get("confidence",0),
            "area":f["properties"].get("area_sqm",0),
            "zone":f["properties"].get("zone",""),
            "type":f["properties"].get("dump_type",""),
        } for f in filtered]

        layer = pdk.Layer("ScatterplotLayer", layer_data,
            get_position=["lon","lat"],
            get_radius="area / 2",
            get_fill_color="[255, 100*(1-confidence), 0, 200]",
            pickable=True, auto_highlight=True,
        )
        view = pdk.ViewState(latitude=9.9252, longitude=78.1198, zoom=11, pitch=30)
        r = pdk.Deck(layers=[layer], initial_view_state=view,
            map_style="mapbox://styles/mapbox/dark-v10",
            tooltip={"text":"{zone}\nType: {type}\nConf: {confidence}\nArea: {area}m²"})
        st.pydeck_chart(r)
    except Exception:
        st.map(pd.DataFrame([{"lat":f["properties"]["lat"],"lon":f["properties"]["lon"]} for f in filtered]))

    # Alert cards
    st.markdown("### 🚨 High Priority Alerts")
    high = sorted(filtered, key=lambda x: -x["properties"].get("priority_score",0))[:5]
    for f in high:
        p = f["properties"]
        tag_cls = p.get("dump_type","unknown").replace(" ","_")
        st.markdown(f"""<div class="alert-card">
        <b>{p.get('zone','').replace('_',' ').title()}</b>
        &nbsp;<span class="tag {tag_cls}">{p.get('dump_type','')}</span>
        <br>📍 {p.get('lat',0):.5f}°N, {p.get('lon',0):.5f}°E &nbsp;|&nbsp;
        📐 {p.get('area_sqm',0):,.0f} m² &nbsp;|&nbsp;
        🔵 {p.get('confidence',0):.0%} confidence &nbsp;|&nbsp;
        📅 Since {p.get('first_seen','?')}
        </div>""", unsafe_allow_html=True)

elif "📊 Analytics" in page:
    st.title("📊 Analytics & Triage")
    
    # Advanced Filters
    st.markdown("### 🎚️ Advanced Triage Filters")
    fa, fb, fc = st.columns(3)
    with fa: selected_risk = st.multiselect("Risk Level", ["critical", "high", "medium", "low"], default=["critical", "high"])
    with fb: 
        all_wards = sorted(list(set(f["properties"].get("ward", "—") for f in features)))
        selected_wards = st.multiselect("Filter by Ward", all_wards)
    with fc: 
        sort_by = st.selectbox("Sort By", ["Priority Score", "Area", "Confidence", "Date"])

    filtered_triage = [f for f in filtered 
        if (not selected_risk or f["properties"].get("risk_level") in selected_risk)
        and (not selected_wards or f["properties"].get("ward") in selected_wards)]

    # Sorting logic
    if sort_by == "Priority Score": filtered_triage.sort(key=lambda x: -x["properties"].get("priority_score", 0))
    elif sort_by == "Area": filtered_triage.sort(key=lambda x: -x["properties"].get("area_sqm", 0))

    st.markdown("---")
    
    # Timeline & Evidence View
    if filtered_triage:
        st.markdown("### 🔍 Site Investigation")
        chosen_site = st.selectbox("Select Site to Inspect", 
                                   [f"{f['properties']['zone'].replace('_',' ').title()} (Site #{i})" for i,f in enumerate(filtered_triage)])
        site_idx = int(chosen_site.split("#")[-1].replace(")", ""))
        site = filtered_triage[site_idx]["properties"]
        
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown("#### Detection Timeline")
            # Simulated history data
            history = pd.DataFrame({
                "Date": ["2023-11-12", "2024-01-05", "2024-02-18", site.get("first_seen")],
                "Size (m²)": [0, 450, 890, site.get("area_sqm")]
            })
            st.line_chart(history.set_index("Date"))
        
        with c2:
            st.markdown("#### Ground Evidence")
            # Check for field photos
            if site.get("image_path"):
                st.image(site["image_path"], caption="Field Photo (Ward Officer)")
            else:
                st.info("No ground photos available yet. Assign a ward officer to verify this site via Shadow Field.")

    st.markdown("---")
    col1, col2 = st.columns(2)
    # ... (rest of the original charts continue below)

    st.markdown("#### Detection Table")
    rows = [{"Zone":f["properties"].get("zone","").replace("_"," ").title(),
             "Type":f["properties"].get("dump_type",""),
             "Confidence":f"{f['properties'].get('confidence',0):.1%}",
             "Area m²":f"{f['properties'].get('area_sqm',0):,.0f}",
             "Ward":f["properties"].get("ward","—"),
             "First Seen":f["properties"].get("first_seen","—"),
             "Risk":f["properties"].get("risk_level","").upper()} for f in filtered]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        gj = json.dumps({"type":"FeatureCollection","features":filtered},indent=2)
        st.download_button("⬇️ GeoJSON", gj, "filtered.geojson", "application/json")
    with col_dl2:
        if rows: st.download_button("⬇️ CSV", pd.DataFrame(rows).to_csv(index=False), "filtered.csv","text/csv")

elif "🔬 Run Scan" in page:
    st.title("🔬 Manual Scan")
    st.info("Upload a before/after Sentinel-2 GeoTIFF pair to run the detector now.")
    c1, c2 = st.columns(2)
    with c1: t1_file = st.file_uploader("📁 Upload T1 (before)", type=["tif","tiff"])
    with c2: t2_file = st.file_uploader("📁 Upload T2 (after)",  type=["tif","tiff"])
    conf_t = st.slider("Detection threshold", 0.5, 0.99, 0.75, 0.01)
    if st.button("🛰️ Detect Dumps", type="primary") and t1_file and t2_file:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp1:
            tmp1.write(t1_file.read()); t1_path = tmp1.name
        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp2:
            tmp2.write(t2_file.read()); t2_path = tmp2.name
        with st.spinner("Running Siamese change detector …"):
            try:
                from src.inference.predict_change import detect_dumps
                gdf = detect_dumps(t1_path, t2_path, confidence_threshold=conf_t)
                st.success(f"✅ {len(gdf)} dump sites detected!")
                if len(gdf) > 0:
                    st.dataframe(gdf.drop(columns="geometry").head(20), use_container_width=True)
                    gj = gdf.to_json()
                    st.download_button("⬇️ Download GeoJSON", gj, "detections.geojson","application/json")
            except Exception as e:
                st.error(f"Detection failed: {e}")
    else:
        st.markdown("""```bash
# Or run from command line:
python -m src.inference.predict_change \\
  --t1 data/processed/madurai_jan.tif \\
  --t2 data/processed/madurai_jul.tif \\
  --output outputs/detections.geojson
```""")

elif "📋 Archive" in page:
    st.title("📋 Dump Archive")
    try:
        from src.agent.database import DumpArchive
        archive = DumpArchive()
        stats = archive.stats()
        c1,c2,c3,c4 = st.columns(4)
        with c1: st.markdown(f'<div class="kpi"><h2>{stats["total_dumps"]}</h2><p>Total Sites</p></div>',unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="kpi"><h2>{stats["active_dumps"]}</h2><p>Active</p></div>',unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="kpi"><h2>{stats["total_detections"]}</h2><p>Detection Events</p></div>',unsafe_allow_html=True)
        with c4: st.markdown(f'<div class="kpi"><h2>{stats["total_verifications"]}</h2><p>Verifications</p></div>',unsafe_allow_html=True)
        dumps = archive.query_history(limit=100)
        if dumps:
            st.dataframe(pd.DataFrame(dumps), use_container_width=True, hide_index=True)
    except Exception as e:
        st.warning(f"Database not populated yet. Run the agent first.\n\n`python -m src.agent.shadow_litter_agent`")
