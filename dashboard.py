import time
import json
import os
import streamlit as st
import pandas as pd

# Page Configuration
st.set_page_config(
    page_title="CrossSafe Command Center",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a sleek, dark-themed command center look
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric {
        background-color: #161b22;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #30363d;
    }
    .alert-box {
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        font-weight: bold;
        font-size: 20px;
        margin-bottom: 20px;
    }
    .occupied { background-color: #da3633; color: white; }
    .clear { background-color: #238636; color: white; }
    </style>
""", unsafe_allow_html=True)

# Sidebar Info
with st.sidebar:
    st.image("https://img.icons8.com/color/96/traffic-light.png", width=80)
    st.title("CrossSafe Hub")
    st.markdown("**Track A:** PipeGen Perception")
    st.markdown("**Site ID:** `CROSSING_01`")
    st.markdown("---")
    auto_refresh = st.checkbox("Enable Live Auto-Refresh", value=True)
    refresh_rate = st.slider("Refresh rate (seconds)", 1, 5, 2)
    st.markdown("---")
    st.info("Hackathon Project: Real-time traffic intelligence and crosswalk safety monitoring.")

st.title("🚦 CrossSafe: Edge Traffic & Crosswalk Intelligence")
st.markdown("Real-time telemetry, vehicle counting, and crosswalk hazard detection.")

events_file = "crosssafe_events.jsonl"

def load_events():
    if not os.path.exists(events_file):
        return []
    events = []
    with open(events_file, "r") as f:
        for line in f:
            if line.strip():
                try:
                    events.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    pass
    return events

# Main Dashboard Layout
placeholder = st.empty()

while True:
    events = load_events()
    
    with placeholder.container():
        if events:
            latest = events[-1]
            is_occupied = latest["event"] == "CROSSWALK_OCCUPIED"
            
            # Status Banner
            status_class = "occupied" if is_occupied else "clear"
            status_text = "🔴 WARNING: CROSSWALK OCCUPIED (Pedestrian Alert)" if is_occupied else "🟢 CROSSWALK CLEAR"
            st.markdown(f'<div class="alert-box {status_class}">{status_text}</div>', unsafe_allow_html=True)
            
            # Metrics Row
            col1, col2, col3, col4 = st.columns(4)
            total_vehicles = sum(1 for e in events if e["event"] == "LINE_CROSSED")
            
            col1.metric("Total Vehicles Counted", total_vehicles, delta="Live Stream")
            col2.metric("Latest Track ID", f"ID #{latest['track_id']}")
            col3.metric("Detection Confidence", f"{latest['confidence']*100:.0f}%")
            col4.metric("Total Event Logs", len(events))
            
            st.markdown("---")
            
            # Charts and Logs Row
            c1, c2 = st.columns([2, 1])
            
            with c1:
                st.subheader("📊 Traffic Activity Timeline")
                df = pd.DataFrame(events)
                if not df.empty and "frame" in df.columns:
                    # Group events by frame chunks for a trend chart
                    chart_data = df['frame'].value_counts().sort_index()
                    st.line_chart(chart_data)
                else:
                    st.info("Gathering more frames for timeline chart...")
            
            with c2:
                st.subheader("📝 Live Event Stream")
                event_logs = [
                    f"**{e['event'].replace('_', ' ')}**\n*Vehicle #{e['track_id']}* ({e['timestamp'][11:19]})"
                    for e in reversed(events[-5:])
                ]
                for log in event_logs:
                    st.markdown(f"> {log}")
                    
        else:
            st.warning("⚠️ No `crosssafe_events.jsonl` found yet. Run your `crosssafe_monitor.py` script to generate live data!")
            
    if not auto_refresh:
        break
    time.sleep(refresh_rate)
    st.rerun()