import streamlit as st
import pandas as pd
import sqlite3
import folium
from streamlit_folium import st_folium
from datetime import datetime
import os

# Page Config
st.set_page_config(
    page_title="Shadow Litter | Madurai Stakeholder Dashboard",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Look
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #161b22;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #30363d;
    }
    .stAlert {
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# DB Helper
def get_db_connection():
    db_path = "data/shadow_litter.db"
    if not os.path.exists(db_path):
        # Create empty if not exists just to avoid crash
        conn = sqlite3.connect(db_path)
        return conn
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def load_data():
    conn = get_db_connection()
    df_dumps = pd.read_sql_query("SELECT * FROM dumps ORDER BY first_seen DESC", conn)
    df_detections = pd.read_sql_query("SELECT * FROM detections ORDER BY detected_at DESC", conn)
    conn.close()
    return df_dumps, df_detections

# Sidebar
st.sidebar.title("🛰️ Shadow Litter")
st.sidebar.markdown("**Orbital Truth for Madurai Smart City**")
st.sidebar.markdown("---")

# Real-Time Scan Trigger
st.sidebar.subheader("Manual Orbital Trigger")
scan_zone = st.sidebar.selectbox("Select Zone", ["vaigai_riverbed", "perungudi_lake", "thiruparankundram", "mattuthavani"])
if st.sidebar.button("🚀 Execute Real-Time Scan"):
    st.sidebar.warning(f"Scan initiated for {scan_zone}. Monitoring GEE task...")

st.sidebar.info("Integration: ESA Copernicus + NASA Prithvi + Madurai Corp.")

# Dashboard Header
st.title("Madurai Civic Observation Console")
st.markdown("*Real satellite intelligence for an illegal-dumping-free city.*")
st.markdown("---")


df_dumps, df_detections = load_data()

# Metrics Row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Dumps", len(df_dumps))
with col2:
    active_count = len(df_dumps[df_dumps['status'] == 'active']) if not df_dumps.empty else 0
    st.metric("Active Sites", active_count, delta_color="inverse")
with col3:
    st.metric("Total Detections", len(df_detections))
with col4:
    st.metric("Confidence (Avg)", f"{df_detections['confidence'].mean():.1%}" if not df_detections.empty else "N/A")

# Main Content: Map and Recent Alerts
col_map, col_alerts = st.columns([2, 1])

with col_map:
    st.subheader("Orbital Intelligence Map")
    # Initialize Map centered on Madurai
    m = folium.Map(location=[9.9252, 78.1198], zoom_start=12, tiles="cartodb dark_matter")
    
    if not df_dumps.empty:
        for idx, row in df_dumps.iterrows():
            color = "red" if row['status'] == 'active' else "green"
            icon = "exclamation-triangle" if row['status'] == 'active' else "check-circle"
            
            folium.Marker(
                [row['lat'], row['lon']],
                popup=f"Zone: {row['zone']}<br>Type: {row['dump_type']}<br>Area: {row['area_sqm']}sqm",
                tooltip=f"{row['zone']} - {row['status']}",
                icon=folium.Icon(color=color, icon=icon, prefix='fa')
            ).add_to(m)
    
    st_folium(m, width=900, height=500)

with col_alerts:
    st.subheader("Recent Alerts")
    if df_dumps.empty:
        st.write("No detections recorded yet.")
    else:
        for idx, row in df_dumps.head(10).iterrows():
            with st.expander(f"📍 {row['zone']} - {row['first_seen'][:10]}"):
                st.write(f"**Type:** {row['dump_type']}")
                st.write(f"**Status:** {row['status']}")
                st.write(f"**Area:** {row['area_sqm']:.1f} m²")
                st.write(f"**Ward:** {row['ward']}")
                st.write(f"[Open in Google Maps](https://www.google.com/maps?q={row['lat']},{row['lon']})")
                if st.button("Verify Site", key=f"btn_{row['id']}"):
                    st.success("Verification logged (Demo Mode)")

# Detailed Data Table
st.markdown("---")
st.subheader("Full Site Registry")
st.dataframe(df_dumps, use_container_width=True)

# Footer
st.markdown("---")
st.caption("Data source: ESA Copernicus Sentinel-2 | NASA Prithvi-100M Foundation Model | Madurai Corporation Integration")
