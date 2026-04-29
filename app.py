import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import random
import math
import time
from datetime import datetime

st.set_page_config(page_title="CAT Autonomous Command", layout="wide", page_icon="🚛")

# Custom CSS for CAT styling
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #1a1a1a 0%, #000000 100%);
    }
    .cat-header {
        background: #ffcd00;
        padding: 15px 30px;
        border-radius: 5px;
        margin-bottom: 20px;
        color: #000;
    }
    .cat-header h1 {
        margin: 0;
        font-family: 'Arial Black', sans-serif;
        display: inline-block;
    }
    .stat-box {
        background: #000;
        border-left: 4px solid #ffcd00;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
    }
    .stat-label {
        font-size: 0.7rem;
        color: #ffcd00;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stat-value {
        font-size: 1.8rem;
        font-weight: bold;
        font-family: monospace;
    }
    .control-panel {
        background: #1a1a1a;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333;
    }
    div.stButton > button {
        background-color: #ffcd00;
        color: #000;
        font-weight: bold;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ============ HEXAGON CLASS ============
class Hexagon:
    def __init__(self, x, y, lane_id, col_id):
        self.x = x
        self.y = y
        self.lane_id = lane_id
        self.col_id = col_id
        self.height = 0.0
        self.locked = False
        self.dump_count = 0
        self.id = f"H{lane_id}-{col_id}"

    def get_color(self):
        if self.height >= 2.4:
            return '#cc0000'
        elif self.height > 0.8:
            return '#0055ff'
        else:
            return '#00cc44'

# ============ TRUCK CLASS WITH COLLISION AVOIDANCE ============
class Truck:
    def __init__(self, truck_id, start_x, start_y, lane_id):
        self.id = f"CAT-{truck_id:03d}"
        self.start_x = start_x
        self.start_y = start_y
        self.x = start_x
        self.y = start_y
        self.lane_id = lane_id
        self.status = "IDLE"
        self.target = None
        self.progress = 0.0
        self.loads = 0
        self.waypoints = []
        self.waiting = False
        self.wait_timer = 0
        self.turning_radius = 25

    def check_collision(self, other_trucks):
        for other in other_trucks:
            if other == self or other.status == "IDLE":
                continue
            distance = math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
            if distance < 35:
                return True
        return False

    def update(self, hexes, all_trucks, stats):
        if self.check_collision(all_trucks):
            self.waiting = True
            self.wait_timer += 1
            if self.wait_timer > 10:
                self.waiting = False
                self.wait_timer = 0
            return
        self.waiting = False
        self.wait_timer = 0
        if self.status == "IDLE":
            targets = [h for h in hexes if h.lane_id == self.lane_id and not h.locked and h.height < 2.4]
            if targets:
                targets.sort(key=lambda h: h.x, reverse=True)
                self.target = targets[0]
                self.target.locked = True
                self.status = "HAULING"
                self.progress = 0.0
                turn_radius = self.turning_radius
                self.waypoints = [
                    (self.start_x, self.start_y),
                    (self.start_x, self.target.y - 15),
                    (self.target.x - turn_radius, self.target.y - 15),
                    (self.target.x, self.target.y)
                ]
        elif self.status == "HAULING":
            self.progress += 0.02
            if len(self.waypoints) >= 4:
                if self.progress < 0.33:
                    t = self.progress / 0.33
                    p1, p2 = self.waypoints[0], self.waypoints[1]
                    self.x = p1[0] + (p2[0] - p1[0]) * t
                    self.y = p1[1] + (p2[1] - p1[1]) * t
                elif self.progress < 0.66:
                    t = (self.progress - 0.33) / 0.33
                    p1, p2 = self.waypoints[1], self.waypoints[2]
                    self.x = p1[0] + (p2[0] - p1[0]) * t
                    self.y = p1[1] + (p2[1] - p1[1]) * t
                else:
                    t = (self.progress - 0.66) / 0.34
                    p1, p2 = self.waypoints[2], self.waypoints[3]
                    self.x = p1[0] + (p2[0] - p1[0]) * t
                    self.y = p1[1] + (p2[1] - p1[1]) * t
            if self.progress >= 1.0:
                self.target.height = min(2.5, self.target.height + 0.6)
                self.target.locked = False
                self.target.dump_count += 1
                self.status = "RETURNING"
                self.progress = 0.0
                stats['tonnage'] += 400
                stats['dumps'] += 1
                self.loads += 1
                turn_radius = self.turning_radius
                self.waypoints = [
                    (self.target.x, self.target.y),
                    (self.target.x - turn_radius, self.target.y),
                    (self.start_x, self.target.y),
                    (self.start_x, self.start_y)
                ]
        elif self.status == "RETURNING":
            self.progress += 0.025
            if len(self.waypoints) >= 4:
                if self.progress < 0.33:
                    t = self.progress / 0.33
                    p1, p2 = self.waypoints[0], self.waypoints[1]
                    self.x = p1[0] + (p2[0] - p1[0]) * t
                    self.y = p1[1] + (p2[1] - p1[1]) * t
                elif self.progress < 0.66:
                    t = (self.progress - 0.33) / 0.33
                    p1, p2 = self.waypoints[1], self.waypoints[2]
                    self.x = p1[0] + (p2[0] - p1[0]) * t
                    self.y = p1[1] + (p2[1] - p1[1]) * t
                else:
                    t = (self.progress - 0.66) / 0.34
                    p1, p2 = self.waypoints[2], self.waypoints[3]
                    self.x = p1[0] + (p2[0] - p1[0]) * t
                    self.y = p1[1] + (p2[1] - p1[1]) * t
            if self.progress >= 1.0:
                self.status = "IDLE"
                self.x = self.start_x
                self.y = self.start_y
                self.target = None

    def get_status_color(self):
        if self.waiting:
            return '#ff6600'
        elif self.status == "HAULING":
            return '#00ff00'
        elif self.status == "RETURNING":
            return '#ffcd00'
        return '#555555'

# ============ CREATE MAP FIGURE ============
def create_map_figure(hexes, trucks):
    fig = go.Figure()
    fig.add_annotation(
        x=0.95, y=0.5, xref='paper', yref='paper',
        text="⬅️ FILLING DIRECTION",
        showarrow=True, arrowhead=2, arrowsize=1.5,
        arrowcolor='#ffcd00', arrowwidth=3,
        font=dict(color='#ffcd00', size=14, family='Arial Black'),
        bgcolor='rgba(0,0,0,0.7)'
    )
    for hex_cell in hexes:
        points = []
        for i in range(6):
            angle_rad = math.radians(60 * i + 30)
            px = hex_cell.x + 14 * math.cos(angle_rad)
            py = hex_cell.y + 14 * math.sin(angle_rad)
            points.append((px, py))
        color = hex_cell.get_color()
        if hex_cell.locked:
            color = '#555555'
        fig.add_trace(go.Scatter(
            x=[p[0] for p in points],
            y=[p[1] for p in points],
            mode='lines', fill='toself',
            fillcolor=color,
            line=dict(color='#333', width=1),
            showlegend=False,
            hoverinfo='text',
            hovertext=f"Lane {hex_cell.lane_id}<br>Height: {hex_cell.height:.2f}m<br>Dumps: {hex_cell.dump_count}"
        ))
    for truck in trucks:
        if truck.status != "IDLE" and truck.target and truck.waypoints:
            fig.add_trace(go.Scatter(
                x=[wp[0] for wp in truck.waypoints],
                y=[wp[1] for wp in truck.waypoints],
                mode='lines',
                line=dict(color='#ffcd00', width=2, dash='dot'),
                showlegend=False,
                hoverinfo='none'
            ))
    for truck in trucks:
        border_color = truck.get_status_color()
        fig.add_trace(go.Scatter(
            x=[truck.x], y=[truck.y],
            mode='markers',
            marker=dict(
                symbol='square', size=32,
                color='rgba(255,205,0,0.2)',
                line=dict(color=border_color, width=2)
            ),
            showlegend=False
        ))
        fig.add_trace(go.Scatter(
            x=[truck.x], y=[truck.y],
            mode='markers+text',
            marker=dict(
                symbol='square', size=28,
                color='#ffcd00',
                line=dict(color=border_color, width=3)
            ),
            text=[truck.id.split('-')[1]],
            textfont=dict(color='#000', size=10, family='Arial Black'),
            textposition='middle center',
            showlegend=False,
            hoverinfo='text',
            hovertext=f"<b>{truck.id}</b><br>Status: {truck.status}{' (WAITING)' if truck.waiting else ''}<br>Loads: {truck.loads}<br>Lane: {truck.lane_id}"
        ))
    fig.update_layout(
        xaxis=dict(
            showgrid=False, zeroline=False,
            fixedrange=True, showticklabels=False,
            scaleanchor='y', scaleratio=1,
            range=[200, 950]
        ),
        yaxis=dict(
            showgrid=False, zeroline=False,
            fixedrange=True, showticklabels=False,
            range=[0, 650]
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=0, b=0),
        height=680,
        dragmode=False,
        # KEY: uirevision prevents the chart from re-initializing on each update,
        # which eliminates the blink / white-flash between frames.
        uirevision='constant'
    )
    return fig

# ============ SIMULATION LOOP FRAGMENT (no full-page rerun) ============
@st.fragment(run_every=0.15)
def simulation_fragment():
    """
    This fragment re-runs every 0.15 s on its own without triggering a
    full-page rerun, so the sidebar and header never blink.
    """
    if not st.session_state.get('initialized') or not st.session_state.get('sim_active'):
        # Still render current state even when paused
        if st.session_state.get('initialized'):
            _render_main_panel()
        return

    # Advance simulation
    for _ in range(2):
        for truck in st.session_state.trucks:
            truck.update(
                st.session_state.hexes,
                st.session_state.trucks,
                st.session_state.stats
            )

    _render_main_panel()


def _render_main_panel():
    """Render the chart + fleet table + metrics into the main column area."""
    hexes  = st.session_state.hexes
    trucks = st.session_state.trucks
    stats  = st.session_state.stats

    fig = create_map_figure(hexes, trucks)
    # use_container_width + uirevision (set in layout) = smooth in-place update
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with st.expander("📋 LIVE FLEET STATUS", expanded=False):
        fleet_data = []
        for truck in trucks:
            if truck.status == 'HAULING':
                status_display = '🟡 HAULING → RIGHT'
            elif truck.status == 'RETURNING':
                status_display = '🟢 RETURNING'
            elif truck.waiting:
                status_display = '🟠 WAITING (Safe Turn)'
            else:
                status_display = '⚪ IDLE'
            target_info = '-'
            if truck.target and hasattr(truck.target, 'x'):
                target_info = f"X:{truck.target.x:.0f}"
            fleet_data.append({
                'TRUCK':    truck.id,
                'STATUS':   status_display,
                'LOADS':    truck.loads,
                'LANE':     truck.lane_id,
                'TARGET X': target_info
            })
        st.dataframe(pd.DataFrame(fleet_data), use_container_width=True, hide_index=True)

    col_info1, col_info2, col_info3, col_info4 = st.columns(4)
    with col_info1:
        st.metric("Filling Direction", "⬅️ RIGHT TO LEFT", delta="Rightmost first")
    with col_info2:
        rightmost_empty = len([h for h in hexes if h.height < 2.4 and h.x > 700])
        st.metric("Right Zone Empty", f"{rightmost_empty}")
    with col_info3:
        st.metric("Live Trucks", f"{len([t for t in trucks if t.status != 'IDLE'])}")
    with col_info4:
        st.metric("Safe Turns", f"{len([t for t in trucks if t.waiting])}")

    st.caption("🔄 LIVE UPDATES | Safe turning radius: 25px | Collision avoidance distance: 35px")


# ============ MAIN APP ============
def main():
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False
    if 'sim_active' not in st.session_state:
        st.session_state.sim_active = False

    # ---- Header (rendered once, never blinks) ----
    st.markdown("""
    <div class="cat-header">
        <h1>CATERPILLAR ®</h1>
        <span style="float: right; background: #000; color: #ffcd00; padding: 5px 10px; border-radius: 3px;">
            SAFE TURNING | COLLISION AVOIDANCE | RIGHT-SIDE FILLING
        </span>
    </div>
    """, unsafe_allow_html=True)

    col_side, col_main = st.columns([1, 3])

    # ---- Sidebar controls (static, never reruns) ----
    with col_side:
        st.markdown('<div class="control-panel">', unsafe_allow_html=True)

        if st.session_state.initialized and st.session_state.sim_active:
            status_text, status_color = "🔥 COLLISION AVOIDANCE ACTIVE", "#00cc44"
        elif st.session_state.initialized:
            status_text, status_color = "⏸️ PAUSED", "#ffcd00"
        else:
            status_text, status_color = "⚪ STANDBY", "#888"

        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">FLEET STATUS</div>
            <div class="stat-value" style="color: {status_color}; font-size: 1.2rem;">{status_text}</div>
        </div>
        """, unsafe_allow_html=True)

        # Live stats placeholders (updated by fragment via session_state)
        tonnage = st.session_state.get('stats', {}).get('tonnage', 0)
        dumps   = st.session_state.get('stats', {}).get('dumps', 0)
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">MATERIAL MOVED (TONS)</div>
            <div class="stat-value">{tonnage:,}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">TOTAL DUMPS</div>
            <div class="stat-value">{dumps}</div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        st.subheader("⚙️ CONFIGURATION")
        yard_width  = st.number_input("Site Width (M)",  300, 800, 500, 20, key="w")
        yard_length = st.number_input("Site Length (M)", 250, 600, 400, 20, key="l")
        num_trucks  = st.number_input("CAT Units (4-15)", 4, 15, 6, 1, key="t")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 START LIVE", type="primary"):
                hex_radius   = 15
                hex_width    = math.sqrt(3) * hex_radius
                vert_spacing = (2 * hex_radius) * 0.75
                rows, cols   = 14, 20
                hexes        = []
                for r in range(rows):
                    lane_id = r // max(1, (rows // max(1, num_trucks)))
                    for c in range(cols):
                        x_off = (hex_width / 2) if r % 2 == 1 else 0
                        x_pos = 280 + c * hex_width + x_off
                        col_from_right = cols - c
                        hexes.append(Hexagon(x_pos, 80 + r * vert_spacing, lane_id, col_from_right))
                trucks = []
                for i in range(num_trucks):
                    lane_hexes = [h for h in hexes if h.lane_id == i]
                    if lane_hexes:
                        avg_y   = sum(h.y for h in lane_hexes) / len(lane_hexes)
                        start_y = avg_y + (i * 5) - (num_trucks * 2.5)
                        trucks.append(Truck(i + 1, 250, start_y, i))
                st.session_state.hexes      = hexes
                st.session_state.trucks     = trucks
                st.session_state.stats      = {'tonnage': 0, 'dumps': 0}
                st.session_state.initialized = True
                st.session_state.sim_active  = True
                st.rerun()

        with col2:
            if st.button("⏹️ STOP"):
                st.session_state.sim_active = False
                st.rerun()

        if st.button("🔄 RESET ALL"):
            for key in ['initialized', 'sim_active', 'hexes', 'trucks', 'stats']:
                st.session_state.pop(key, None)
            st.rerun()

        st.markdown("---")

        if st.session_state.initialized:
            filled   = len([h for h in st.session_state.hexes if h.height >= 2.4])
            total    = len(st.session_state.hexes)
            progress = (filled / total) * 100 if total > 0 else 0
            st.progress(progress / 100)
            st.caption(f"📊 SITE FILL: {filled}/{total} ({progress:.1f}%)")
            active  = len([t for t in st.session_state.trucks if t.status != "IDLE"])
            waiting = len([t for t in st.session_state.trucks if t.waiting])
            st.caption(f"🚛 ACTIVE TRUCKS: {active} | ⏳ WAITING: {waiting}")
            st.info("✅ Safe turning enabled | Collision avoidance active")

        st.markdown("""
        <div style="margin-top: 20px;">
            <p style="color:#ffcd00; font-size:12px;">LEGEND</p>
            <div><span style="background:#cc0000; width:12px; height:12px; display:inline-block;"></span> Full (&gt;2.4m)</div>
            <div><span style="background:#0055ff; width:12px; height:12px; display:inline-block;"></span> Filling</div>
            <div><span style="background:#00cc44; width:12px; height:12px; display:inline-block;"></span> Empty</div>
            <div><span style="background:#ffcd00; width:12px; height:12px; display:inline-block;"></span> CAT Truck</div>
            <div><span style="background:#ff6600; width:12px; height:12px; display:inline-block;"></span> Waiting/Safe Turn</div>
            <div><span style="background:transparent; border:1px dashed #ffcd00; width:12px; height:12px; display:inline-block;"></span> Planned Route</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ---- Main panel: simulation fragment runs here ----
    with col_main:
        if st.session_state.initialized:
            simulation_fragment()
        else:
            st.info("👈 CONFIGURE SETTINGS & CLICK 'START LIVE'")
            st.markdown("""
            <div style="text-align: center; padding: 50px; background: #1a1a1a; border-radius: 10px;">
                <h2 style="color: #ffcd00;">🚛 CAT AUTONOMOUS COMMAND</h2>
                <p style="color: #fff;">SAFE TURNING | COLLISION AVOIDANCE SYSTEM</p>
                <p style="color: #00cc44;">⬅️ DUMPYARD STARTS COMPLETELY EMPTY ⬅️</p>
                <p style="color: #888;">Trucks fill from RIGHT side | Wide turning arcs | Automatic collision prevention</p>
                <p style="color: #ffcd00;">⬅️ FILLING DIRECTION: RIGHT → LEFT ⬅️</p>
            </div>
            """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
