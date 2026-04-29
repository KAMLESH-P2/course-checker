import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="CAT Autonomous Command", layout="wide", page_icon="🚛")

st.markdown("""
<style>
    .stApp { background: #0d0d0d; }
    .cat-header {
        background: #ffcd00; padding: 12px 28px;
        border-radius: 5px; margin-bottom: 16px; color: #000;
        display: flex; align-items: center; justify-content: space-between;
    }
    .cat-header h1 { margin: 0; font-family: 'Arial Black', sans-serif; font-size: 1.6rem; }
    .badge { background:#000; color:#ffcd00; padding:5px 12px; border-radius:3px; font-size:.8rem; font-weight:bold; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="cat-header">
  <h1>🚛 CATERPILLAR ® AUTONOMOUS COMMAND</h1>
  <span class="badge">SAFE TURNING | COLLISION AVOIDANCE | RIGHT-SIDE FILLING</span>
</div>
""", unsafe_allow_html=True)

col_cfg, col_sim = st.columns([1, 3])

with col_cfg:
    st.markdown("### ⚙️ Configuration")
    num_trucks     = st.slider("CAT Units", 4, 15, 6)
    update_ms      = st.slider("Update Speed (ms)", 100, 5000, 300, step=100,
                               help="Higher = slower/smoother, less CPU")
    steps_per_tick = st.slider("Steps per tick", 1, 5, 2,
                               help="Simulation steps computed per update")
    st.button("🚀 Apply & Restart", type="primary", use_container_width=True)

    st.markdown("---")
    st.markdown("""
    <div style='color:#ccc; font-size:.85rem; line-height:2'>
    <b style='color:#ffcd00'>LEGEND</b><br>
    🟥 Full (&gt;2.4 m)<br>
    🟦 Filling<br>
    🟩 Empty<br>
    🟨 CAT Truck<br>
    🟧 Waiting / Safe Turn<br>
    </div>
    """, unsafe_allow_html=True)

# ─── Build self-contained HTML+JS (runs entirely in the browser) ───────────
HTML = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  body  {{ margin:0; background:#111; font-family:monospace; color:#fff; overflow:hidden; }}
  #stats{{ display:flex; gap:12px; padding:8px 6px; flex-wrap:wrap; }}
  .stat {{ background:#000; border-left:4px solid #ffcd00; padding:6px 12px; border-radius:4px; min-width:100px; }}
  .stat-label {{ font-size:.6rem; color:#ffcd00; text-transform:uppercase; letter-spacing:1px; }}
  .stat-value {{ font-size:1.3rem; font-weight:bold; }}
  #map  {{ width:100%; height:520px; }}
  #bar  {{ padding:3px 8px; font-size:.72rem; color:#666; border-top:1px solid #222; }}
</style>
</head>
<body>

<div id="stats">
  <div class="stat"><div class="stat-label">Material Moved</div><div class="stat-value" id="s-t">0 t</div></div>
  <div class="stat"><div class="stat-label">Total Dumps</div><div class="stat-value" id="s-d">0</div></div>
  <div class="stat"><div class="stat-label">Active Trucks</div><div class="stat-value" id="s-a">0</div></div>
  <div class="stat"><div class="stat-label">Waiting</div><div class="stat-value" id="s-w">0</div></div>
  <div class="stat"><div class="stat-label">Site Fill</div><div class="stat-value" id="s-f">0%</div></div>
</div>
<div id="map"></div>
<div id="bar">⏳ Initialising…</div>

<script>
// ══════════════════════════════════════════════
// CONFIG  (values injected by Python)
// ══════════════════════════════════════════════
const NUM_TRUCKS     = {num_trucks};
const UPDATE_MS      = {update_ms};
const STEPS_PER_TICK = {steps_per_tick};
const HEX_R  = 14;
const HEX_W  = Math.sqrt(3) * HEX_R;
const VSPACE = 2 * HEX_R * 0.75;
const ROWS   = 14, COLS = 20;
const TURN_R = 25, COLL_DIST = 35;

// ══════════════════════════════════════════════
// STATE
// ══════════════════════════════════════════════
let hexes=[], trucks=[], stats={{tonnage:0,dumps:0}};

function init() {{
  hexes=[]; trucks=[]; stats={{tonnage:0,dumps:0}};

  for (let r=0;r<ROWS;r++) {{
    const lane = Math.floor(r / Math.max(1, Math.floor(ROWS/NUM_TRUCKS)));
    for (let c=0;c<COLS;c++) {{
      const xoff = (r%2===1) ? HEX_W/2 : 0;
      hexes.push({{ x:280+c*HEX_W+xoff, y:80+r*VSPACE,
                    lane, col:COLS-c, height:0, locked:false, dumps:0 }});
    }}
  }}

  for (let i=0;i<NUM_TRUCKS;i++) {{
    const lh = hexes.filter(h=>h.lane===i);
    const ay = lh.length ? lh.reduce((s,h)=>s+h.y,0)/lh.length : 300;
    const sy = ay + i*5 - NUM_TRUCKS*2.5;
    trucks.push({{ id:`CAT-${{String(i+1).padStart(3,'0')}}`,
                   sx:250, sy, x:250, y:sy, lane:i,
                   status:'IDLE', target:null, progress:0,
                   loads:0, wps:[], waiting:false, wt:0 }});
  }}
}}

// ══════════════════════════════════════════════
// PHYSICS
// ══════════════════════════════════════════════
function collides(t) {{
  for (const o of trucks) {{
    if (o===t||o.status==='IDLE') continue;
    const dx=t.x-o.x, dy=t.y-o.y;
    if (dx*dx+dy*dy < COLL_DIST*COLL_DIST) return true;
  }}
  return false;
}}

function lerp3(wps, p) {{
  const seg = p<0.33 ? 0 : p<0.66 ? 1 : 2;
  const s0  = seg===0?0:seg===1?0.33:0.66;
  const s1  = seg===0?0.33:seg===1?0.66:1.0;
  const t   = (p-s0)/(s1-s0);
  const a=wps[seg], b=wps[seg+1];
  return [a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t];
}}

function stepTruck(t) {{
  if (collides(t)) {{
    t.waiting=true; t.wt++;
    if (t.wt>10){{t.waiting=false;t.wt=0;}}
    return;
  }}
  t.waiting=false; t.wt=0;

  if (t.status==='IDLE') {{
    const cands = hexes.filter(h=>h.lane===t.lane&&!h.locked&&h.height<2.4);
    if (!cands.length) return;
    cands.sort((a,b)=>b.x-a.x);
    const tgt=cands[0]; tgt.locked=true;
    t.target=tgt; t.status='HAULING'; t.progress=0;
    t.wps=[[t.sx,t.sy],[t.sx,tgt.y-15],[tgt.x-TURN_R,tgt.y-15],[tgt.x,tgt.y]];

  }} else if (t.status==='HAULING') {{
    t.progress+=0.02;
    [t.x,t.y]=lerp3(t.wps,Math.min(t.progress,0.9999));
    if (t.progress>=1) {{
      const g=t.target;
      g.height=Math.min(2.5,g.height+0.6); g.locked=false; g.dumps++;
      stats.tonnage+=400; stats.dumps++; t.loads++;
      t.status='RETURNING'; t.progress=0;
      t.wps=[[g.x,g.y],[g.x-TURN_R,g.y],[t.sx,g.y],[t.sx,t.sy]];
    }}

  }} else if (t.status==='RETURNING') {{
    t.progress+=0.025;
    [t.x,t.y]=lerp3(t.wps,Math.min(t.progress,0.9999));
    if (t.progress>=1) {{
      t.status='IDLE'; t.x=t.sx; t.y=t.sy; t.target=null;
    }}
  }}
}}

function simStep() {{
  for (let s=0;s<STEPS_PER_TICK;s++)
    for (const t of trucks) stepTruck(t);
}}

// ══════════════════════════════════════════════
// RENDERING  — Plotly.react() does a diff,
// so only changed traces are redrawn.
// uirevision='x' keeps zoom/pan state stable.
// Result: ZERO full-page flicker.
// ══════════════════════════════════════════════
function hexPts(h) {{
  const xs=[],ys=[];
  for(let i=0;i<6;i++){{
    const a=Math.PI/180*(60*i+30);
    xs.push(h.x+HEX_R*Math.cos(a));
    ys.push(h.y+HEX_R*Math.sin(a));
  }}
  xs.push(xs[0]);ys.push(ys[0]);
  return {{xs,ys}};
}}

function hxColor(h) {{
  if(h.locked)      return '#555';
  if(h.height>=2.4) return '#cc0000';
  if(h.height>0.8)  return '#0055ff';
  return '#00cc44';
}}

function tkColor(t) {{
  if(t.waiting)            return '#ff6600';
  if(t.status==='HAULING') return '#00ff00';
  if(t.status==='RETURNING') return '#ffcd00';
  return '#555';
}}

function buildTraces() {{
  const tr=[];

  // hexagons
  for(const h of hexes) {{
    const {{xs,ys}}=hexPts(h);
    tr.push({{ x:xs,y:ys,type:'scatter',mode:'lines',fill:'toself',
               fillcolor:hxColor(h),line:{{color:'#333',width:1}},
               showlegend:false,hoverinfo:'text',
               hovertext:`Lane ${{h.lane}}<br>H: ${{h.height.toFixed(2)}}m` }});
  }}

  // paths
  for(const t of trucks) {{
    if(t.status!=='IDLE'&&t.target&&t.wps.length)
      tr.push({{ x:t.wps.map(w=>w[0]),y:t.wps.map(w=>w[1]),
                 type:'scatter',mode:'lines',
                 line:{{color:'#ffcd00',width:1.5,dash:'dot'}},
                 showlegend:false,hoverinfo:'none' }});
  }}

  // trucks
  for(const t of trucks) {{
    tr.push({{ x:[t.x],y:[t.y],type:'scatter',mode:'markers+text',
               marker:{{symbol:'square',size:24,color:'#ffcd00',
                        line:{{color:tkColor(t),width:3}}}},
               text:[t.id.split('-')[1]],
               textfont:{{color:'#000',size:9,family:'Arial Black'}},
               textposition:'middle center',showlegend:false,
               hoverinfo:'text',
               hovertext:`<b>${{t.id}}</b><br>${{t.status}}${{t.waiting?' ⚠':''}}<br>Loads: ${{t.loads}}` }});
  }}

  return tr;
}}

const LAYOUT={{
  xaxis:{{showgrid:false,zeroline:false,fixedrange:true,showticklabels:false,
          scaleanchor:'y',scaleratio:1,range:[200,950]}},
  yaxis:{{showgrid:false,zeroline:false,fixedrange:true,showticklabels:false,range:[0,650]}},
  plot_bgcolor:'rgba(0,0,0,0)', paper_bgcolor:'rgba(0,0,0,0)',
  margin:{{l:0,r:0,t:0,b:0}}, height:520, dragmode:false,
  uirevision:'x',   // ← KEY: prevents Plotly tearing down the canvas each frame
  annotations:[{{
    x:.95,y:.5,xref:'paper',yref:'paper',
    text:'⬅️ FILLING DIRECTION',showarrow:true,arrowhead:2,
    arrowsize:1.5,arrowcolor:'#ffcd00',arrowwidth:3,
    font:{{color:'#ffcd00',size:12,family:'Arial Black'}},
    bgcolor:'rgba(0,0,0,.7)'
  }}]
}};

let inited=false;

function renderFrame() {{
  const traces=buildTraces();
  if(!inited) {{
    Plotly.newPlot('map',traces,LAYOUT,{{displayModeBar:false,responsive:true}});
    inited=true;
  }} else {{
    // react() diffs old vs new traces — no full canvas wipe, no flash
    Plotly.react('map',traces,LAYOUT,{{displayModeBar:false,responsive:true}});
  }}

  // stats
  const filled=hexes.filter(h=>h.height>=2.4).length;
  document.getElementById('s-t').textContent=stats.tonnage.toLocaleString()+' t';
  document.getElementById('s-d').textContent=stats.dumps;
  document.getElementById('s-a').textContent=trucks.filter(t=>t.status!=='IDLE').length;
  document.getElementById('s-w').textContent=trucks.filter(t=>t.waiting).length;
  document.getElementById('s-f').textContent=(filled/hexes.length*100).toFixed(1)+'%';
  document.getElementById('bar').textContent=
    `🔄 every ${{UPDATE_MS}} ms · ${{STEPS_PER_TICK}} steps/tick · ${{filled}}/${{hexes.length}} cells filled`;
}}

function tick() {{ simStep(); renderFrame(); }}

init();
renderFrame();
setInterval(tick, UPDATE_MS);
</script>
</body>
</html>"""

with col_sim:
    components.html(HTML, height=670, scrolling=False)
