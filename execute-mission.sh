#!/bin/bash
# execute-mission.sh

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     SHADOW LITTER: REAL DATA MISSION EXECUTION             ║"
echo "╚════════════════════════════════════════════════════════════╝"

export PYTHONPATH=$(pwd)
source venv/bin/activate

# Pre-flight
echo "🔍 PRE-FLIGHT CHECKS..."
python -c "from preflight import verify_all; verify_all()" || exit 1

# Phase 1: Data
echo -e "\n📡 ACQUIRING LIVE SATELLITE DATA..."
python -m shadow_litter.mission.phase1_data_acquisition

# Phase 2: AI
echo -e "\n🧠 EXECUTING AI INFERENCE..."
python -m shadow_litter.mission.phase2_ai_processing

# Phase 3: Alerts
echo -e "\n🚨 DELIVERING REAL-WORLD ALERTS..."
python -m shadow_litter.mission.phase3_alert_delivery

# Phase 4: Validation
echo -e "\n✅ VALIDATING END-TO-END..."
python -m shadow_litter.mission.phase4_validation

# Report
echo -e "\n📊 GENERATING MISSION REPORT..."
python -m shadow_litter.mission.phase5_report

echo -e "\n🏁 MISSION COMPLETE"
