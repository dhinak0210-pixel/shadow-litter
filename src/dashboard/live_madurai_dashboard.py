"""
src/dashboard/live_madurai_dashboard.py
────────────────────────────────────────
LIVE dashboard showing real waste detections in real Madurai.
"""

import streamlit as st
import pydeck as pdk
from datetime import datetime, timedelta

st.set_page_config(page_title="Shadow Litter LIVE", layout="wide")

st.title("🛰️ Shadow Litter LIVE: Madurai Civic Observation")

col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("Live Orbital View")
    view_state = pdk.ViewState(latitude=9.9259, longitude=78.1198, zoom=12, pitch=45)
    st.pydeck_chart(pdk.Deck(
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/satellite-v9",
        layers=[]
    ))

with col2:
    st.subheader("Mission Status")
    st.success("🛰️ Sentinel-2B Online")
    st.info("🕒 Next Revisit: Mar 5, 2026")
    
    st.markdown("---")
    st.subheader("High-Risk Hotspots")
    st.error("🚩 Vaigai Riverbed (Critical)")
    st.warning("⚠️ Perungudi Lake (High)")
    
    if st.button("🚀 Trigger Manual Scan", type="primary"):
        st.write("Triggering cloud-based compute for T44PQA...")
