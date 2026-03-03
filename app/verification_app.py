"""
app/verification_app.py
────────────────────────
Shadow Litter Explorer — Crowd verification Streamlit app.
Citizens and researchers verify AI detections with Yes/No/Unsure votes.
Points + leaderboard system.
"""
import json, random
from pathlib import Path
from datetime import datetime
import streamlit as st
import numpy as np

st.set_page_config(page_title="Shadow Litter Explorer", page_icon="🔍", layout="centered")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
*{font-family:'Inter',sans-serif}
[data-testid="stAppViewContainer"]{background:#0a0f1e;color:#e0e6f0}
.verdict-btn{padding:.8rem 2rem;border-radius:10px;font-size:1.1rem;font-weight:700;cursor:pointer;border:none}
.score-card{background:rgba(20,40,80,0.4);border:1px solid #1e3a5f;border-radius:12px;padding:1rem;text-align:center}
</style>
""", unsafe_allow_html=True)

# ── Session state init ─────────────────────────────────────────────────────────
if "user_id" not in st.session_state:
    st.session_state.user_id = f"explorer_{random.randint(10000,99999)}"
if "score" not in st.session_state:
    st.session_state.score = 0
if "votes_cast" not in st.session_state:
    st.session_state.votes_cast = 0

# ── Load detections ────────────────────────────────────────────────────────────
def load_pending() -> list[dict]:
    """Load unverified detections from database or demo data."""
    try:
        from src.agent.database import DumpArchive
        archive = DumpArchive()
        dumps = archive.query_history(status="active", limit=50)
        return [d for d in dumps if archive.verification_summary(d["id"]).get("yes",0) < 2]
    except Exception:
        return [
            {"id":1,"zone":"vaigai_riverbed","lat":9.9259,"lon":78.1198,"first_seen":"2024-03-15","area_sqm":1240,"dump_type":"fresh_dump"},
            {"id":2,"zone":"thiruparankundram_quarries","lat":9.8765,"lon":78.0734,"first_seen":"2024-02-20","area_sqm":4500,"dump_type":"construction_debris"},
        ]

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("🔍 Shadow Litter Explorer")
st.markdown("**Help verify AI detections. Each vote improves the model.**")

c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="score-card"><h2 style="color:#4fc3f7">{st.session_state.score}</h2><p>Your Points</p></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="score-card"><h2 style="color:#4fc3f7">{st.session_state.votes_cast}</h2><p>Votes Cast</p></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="score-card"><h2 style="color:#4fc3f7">🔍</h2><p>ID: {st.session_state.user_id}</p></div>', unsafe_allow_html=True)

st.markdown("---")

# ── Current detection ──────────────────────────────────────────────────────────
pending = load_pending()
if not pending:
    st.success("🎉 All current detections have been verified! Check back after the next scan.")
    st.stop()

# Pick a random unverified one (avoid repeats via session)
seen = st.session_state.get("seen_ids", set())
unseen = [d for d in pending if d["id"] not in seen]
if not unseen:
    st.session_state.seen_ids = set()
    unseen = pending

current = unseen[0]
seen.add(current["id"]); st.session_state.seen_ids = seen

st.markdown(f"### Detection #{current['id']}: {current['zone'].replace('_',' ').title()}")
st.markdown(f"""
| | |
|---|---|
| **📍 Location** | {current['lat']:.5f}°N, {current['lon']:.5f}°E |
| **📅 First seen** | {current['first_seen']} |
| **📐 Area** | {current.get('area_sqm',0):,} m² |
| **🏷️ AI classification** | {current.get('dump_type','unknown')} |
| **🗺️ Map** | [View on Google Maps](https://maps.google.com/?q={current['lat']},{current['lon']}) |
""")

# Simulated before/after images (replace with real satellite crops)
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Before**")
    before = np.ones((128, 128, 3), np.uint8) * 40
    before[40:90, 30:100] = [20, 80, 20]  # green veg
    st.image(before, caption="Baseline (green = vegetation)", use_column_width=True)
with c2:
    st.markdown("**After**")
    after = np.ones((128, 128, 3), np.uint8) * 40
    after[40:90, 30:100] = [20, 80, 20]
    after[50:80, 45:85] = [120, 90, 60]  # brownish dump
    st.image(after, caption="Latest (brown = suspected dump)", use_column_width=True)

st.markdown("---")
st.markdown("### Is this a real dump site?")

def record_vote(vote: str):
    try:
        from src.agent.database import DumpArchive
        DumpArchive().add_verification(current["id"], st.session_state.user_id, vote)
    except Exception:
        pass  # log only
    st.session_state.votes_cast += 1
    points = {"yes": 10, "no": 8, "unsure": 3}[vote]
    st.session_state.score += points
    st.rerun()

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("✅ Yes, it's a dump", use_container_width=True, type="primary"):
        record_vote("yes")
with col2:
    if st.button("❌ Not a dump", use_container_width=True):
        record_vote("no")
with col3:
    if st.button("🤷 Unsure", use_container_width=True):
        record_vote("unsure")

st.markdown("---")
st.caption(f"Session ID: `{st.session_state.user_id}` · Your votes are anonymous and used to improve detection accuracy.")
