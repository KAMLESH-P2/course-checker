import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="CAT Autonomous Command", layout="wide", page_icon="🚛")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg,#1a1a1a 0%,#000 100%); }
    section[data-testid="stSidebar"] { display:none; }
    header { background:transparent !important; }
</style>
""", unsafe_allow_html=True)

# Everything lives inside one self-contained HTML component — zero Streamlit reruns = zero blink
HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
* { box-sizing: border-box; margin:0; padding:0; }
body {
  background: linear-gradient(135deg,#1a1a1a 0%,#000 100%);
  font-family: Arial, sans-serif;
  color: #fff;
  height: 100vh;
  overflow: hidden;
}

/* ── HEADER ── */
#header {
  background: #ffcd00;
  padding: 10px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-radius: 5px;
  margin: 6px 6px 8px 6px;
}
#header h1 { font-family:'Arial Black',sans-serif; font-size:1.3rem; color:#000; }
#header .badge {
  background:#000; color:#ffcd00;
  padding:4px 10px; border-radius:3px; font-size:.72rem; font-weight:bold;
}

/* ── MAIN LAYOUT ── */
#main { display:flex; gap:8px; padding:0 6px 6px 6px; height: calc(100vh - 72px); }

/* ── LEFT PANEL ── */
#left {
  width: 240px; min-width:220px;
  background:#1a1a1a; border:1px solid #333;
  border-radius:10px; padding:14px 12px;
  display:flex; flex-direction:column; gap:10px;
  overflow-y:auto;
}

.stat-box {
  background:#000; border-left:4px solid #ffcd00;
  padding:10px 12px; border-radius:5px;
}
.stat-label { font-size:.62rem; color:#ffcd00; text-transform:uppercase; letter-spacing:1px; }
.stat-value { font-size:1.5rem; font-weight:bold; font-family:monospace; }

.section-title {
  color:#ffcd00; font-size:.78rem;
  text-transform:uppercase; letter-spacing:1px;
  border-bottom:1px solid #333; padding-bottom:4px;
}

label { font-size:.78rem; color:#aaa; display:block; margin-bottom:2px; margin-top:6px; }
input[type=number] {
  width:100%; background:#000; border:1px solid #444;
  color:#fff; padding:5px 8px; border-radius:4px; font-size:.9rem;
}
input[type=range] { width:100%; accent-color:#ffcd00; }
.range-val { color:#ffcd00; font-size:.8rem; font-weight:bold; float:right; }

/* Buttons */
.btn {
  width:100%; padding:8px; border:none; border-radius:5px;
  font-weight:bold; font-size:.85rem; cursor:pointer; margin-top:4px;
}
.btn-start  { background:#ffcd00; color:#000; }
.btn-stop   { background:#333; color:#fff; border:1px solid #555; }
.btn-reset  { background:#1a1a1a; color:#ffcd00; border:1px solid #ffcd00; }
.btn:disabled { opacity:.4; cursor:not-allowed; }

/* Progress bar */
#prog-wrap {
  background:#222; border-radius:4px; height:10px; overflow:hidden; margin-top:2px;
}
#prog-bar {
  height:100%; background:#ffcd00; width:0%; transition:width .4s;
}
#prog-label { font-size:.7rem; color:#aaa; margin-top:2px; }

/* Fleet table */
#fleet-wrap {
  overflow-x:auto; overflow-y:auto; max-height:160px;
}
table { width:100%; border-collapse:collapse; font-size:.68rem; }
th { background:#000; color:#ffcd00; padding:3px 5px; text-align:left; position:sticky; top:0; }
td { padding:3px 5px; border-bottom:1px solid #222; color:#ccc; }
tr:hover td { background:#111; }

/* Legend */
.legend-item { display:flex; align-items:center; gap:6px; font-size:.75rem; color:#ccc; margin:2px 0; }
.legend-dot  { width:12px; height:12px; border-radius:2px; flex-shrink:0; }

/* ── RIGHT PANEL ── */
#right { flex:1; display:flex; flex-direction:column; gap:6px; min-width:0; }

#status-row {
  display:flex; gap:8px; flex-wrap:wrap;
}
.metric {
  background:#000; border-left:3px solid #ffcd00;
  padding:6px 12px; border-radius:4px; flex:1; min-width:100px;
}
.metric-label { font-size:.6rem; color:#ffcd00; text-transform:uppercase; letter-spacing:1px; }
.metric-value { font-size:1.1rem; font-weight:bold; font-family:monospace; }
.metric-delta { font-size:.65rem; color:#00cc44; }

#map  { flex:1; min-height:0; }
#statusbar {
  font-size:.7rem; color:#555; padding:2px 4px;
  border-top:1px solid #222;
}

/* Splash screen */
#splash {
  flex:1; display:flex; align-items:center; justify-content:center;
  background:#1a1a1a; border-radius:10px; border:1px solid #333;
}
#splash-inner { text-align:center; }
#splash-inner h2 { color:#ffcd00; font-family:'Arial Black',sans-serif; margin-bottom:8px; }
#splash-inner p  { color:#888; font-size:.85rem; margin:4px 0; }
.green { color:#00cc44; }
</style>
</head>
<body>

<!-- HEADER -->
<div id="header">
  <h1>🚛 CATERPILLAR ®</h1>
  <span class="badge">SAFE TURNING &nbsp;|&nbsp; COLLISION AVOIDANCE &nbsp;|&nbsp; RIGHT-SIDE FILLING</span>
</div>

<!-- MAIN -->
<div id="main">

  <!-- LEFT CONTROL PANEL -->
  <div id="left">

    <!-- Fleet status indicator -->
    <div class="stat-box">
      <div class="stat-label">Fleet Status</div>
      <div class="stat-value" id="fleet-status" style="font-size:1rem;color:#888">⚪ STANDBY</div>
    </div>

    <!-- Material / dumps -->
    <div class="stat-box">
      <div class="stat-label">Material Moved (tons)</div>
      <div class="stat-value" id="s-tonnage">0</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Total Dumps</div>
      <div class="stat-value" id="s-dumps">0</div>
    </div>

    <div class="section-title">⚙️ Configuration</div>

    <div>
      <label>Site Width (m)</label>
      <input type="number" id="cfg-width" value="500" min="300" max="800" step="20">
    </div>
    <div>
      <label>Site Length (m)</label>
      <input type="number" id="cfg-length" value="400" min="250" max="600" step="20">
    </div>
    <div>
      <label>CAT Units (4–15)</label>
      <input type="number" id="cfg-trucks" value="6" min="4" max="15" step="1">
    </div>
    <div>
      <label>Update Speed <span class="range-val" id="lbl-speed">300 ms</span></label>
      <input type="range" id="cfg-speed" min="100" max="3000" step="100" value="300">
    </div>

    <button class="btn btn-start" id="btn-start" onclick="handleStart()">🚀 START LIVE</button>
    <button class="btn btn-stop"  id="btn-stop"  onclick="handleStop()"  disabled>⏹️ STOP</button>
    <button class="btn btn-reset" id="btn-reset" onclick="handleReset()" disabled>🔄 RESET ALL</button>

    <div style="margin-top:4px">
      <div class="stat-label" style="margin-bottom:4px">📊 Site Fill</div>
      <div id="prog-wrap"><div id="prog-bar"></div></div>
      <div id="prog-label">0 / 0 (0.0%)</div>
    </div>

    <div class="section-title">📋 Fleet Status</div>
    <div id="fleet-wrap">
      <table id="fleet-table">
        <thead><tr>
          <th>TRUCK</th><th>STATUS</th><th>LOADS</th><th>LANE</th>
        </tr></thead>
        <tbody id="fleet-body"></tbody>
      </table>
    </div>

    <div class="section-title" style="margin-top:4px">Legend</div>
    <div class="legend-item"><div class="legend-dot" style="background:#cc0000"></div> Full (&gt;2.4 m)</div>
    <div class="legend-item"><div class="legend-dot" style="background:#0055ff"></div> Filling</div>
    <div class="legend-item"><div class="legend-dot" style="background:#00cc44"></div> Empty</div>
    <div class="legend-item"><div class="legend-dot" style="background:#ffcd00"></div> CAT Truck</div>
    <div class="legend-item"><div class="legend-dot" style="background:#ff6600"></div> Waiting / Safe Turn</div>
    <div class="legend-item">
      <div class="legend-dot" style="background:transparent;border:1px dashed #ffcd00"></div>
      Planned Route
    </div>
  </div>

  <!-- RIGHT MAP AREA -->
  <div id="right">

    <!-- Metric row -->
    <div id="status-row">
      <div class="metric">
        <div class="metric-label">Filling Direction</div>
        <div class="metric-value">⬅️ R→L</div>
        <div class="metric-delta">Rightmost first</div>
      </div>
      <div class="metric">
        <div class="metric-label">Right Zone Empty</div>
        <div class="metric-value" id="m-rzone">—</div>
      </div>
      <div class="metric">
        <div class="metric-label">Live Trucks</div>
        <div class="metric-value" id="m-live">—</div>
      </div>
      <div class="metric">
        <div class="metric-label">Safe Turns</div>
        <div class="metric-value" id="m-safe">—</div>
      </div>
      <div class="metric">
        <div class="metric-label">Collision Avoidance</div>
        <div class="metric-value" style="color:#00cc44">✅ ON</div>
      </div>
    </div>

    <!-- Map or splash -->
    <div id="map-container" style="flex:1;min-height:0;display:flex;flex-direction:column;">
      <!-- splash shown before start -->
      <div id="splash">
        <div id="splash-inner">
          <h2>🚛 CAT AUTONOMOUS COMMAND</h2>
          <p>SAFE TURNING &nbsp;|&nbsp; COLLISION AVOIDANCE SYSTEM</p>
          <p class="green">⬅️ DUMPYARD STARTS COMPLETELY EMPTY ⬅️</p>
          <p style="color:#888">Configure settings & click START LIVE</p>
          <p style="color:#ffcd00;margin-top:8px">⬅️ FILLING DIRECTION: RIGHT → LEFT ⬅️</p>
        </div>
      </div>
      <!-- map (hidden until started) -->
      <div id="map" style="display:none;flex:1;min-height:0;"></div>
    </div>

    <div id="statusbar">⏳ Waiting for start…</div>
  </div>

</div><!-- /main -->

<script>
// ══════════════════════════════════════════════════════════
// CONSTANTS
// ══════════════════════════════════════════════════════════
const HEX_R    = 14;
const HEX_W    = Math.sqrt(3) * HEX_R;
const VSPACE   = 2 * HEX_R * 0.75;
const ROWS     = 14, COLS = 20;
const TURN_R   = 25, COLL_DIST = 35;

// ══════════════════════════════════════════════════════════
// STATE
// ══════════════════════════════════════════════════════════
let hexes=[], trucks=[], stats={tonnage:0,dumps:0};
let simTimer=null, running=false, plotInited=false;

// ── speed slider live label ──
document.getElementById('cfg-speed').addEventListener('input', function(){
  document.getElementById('lbl-speed').textContent = this.value + ' ms';
});

// ══════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════
function initSim() {
  const numTrucks = clamp(parseInt(document.getElementById('cfg-trucks').value)||6, 4, 15);
  hexes=[]; trucks=[]; stats={tonnage:0,dumps:0};

  for (let r=0;r<ROWS;r++) {
    const lane = Math.floor(r / Math.max(1, Math.floor(ROWS/numTrucks)));
    for (let c=0;c<COLS;c++) {
      const xoff = (r%2===1) ? HEX_W/2 : 0;
      hexes.push({ x:280+c*HEX_W+xoff, y:80+r*VSPACE,
                   lane, height:0, locked:false, dumps:0 });
    }
  }

  for (let i=0;i<numTrucks;i++) {
    const lh = hexes.filter(h=>h.lane===i);
    const ay = lh.length ? lh.reduce((s,h)=>s+h.y,0)/lh.length : 300;
    const sy = ay + i*5 - numTrucks*2.5;
    trucks.push({ id:`CAT-${String(i+1).padStart(3,'0')}`,
                  sx:250, sy, x:250, y:sy, lane:i,
                  status:'IDLE', target:null, progress:0,
                  loads:0, wps:[], waiting:false, wt:0 });
  }
}

function clamp(v,lo,hi){ return Math.max(lo,Math.min(hi,v)); }

// ══════════════════════════════════════════════════════════
// PHYSICS
// ══════════════════════════════════════════════════════════
function collides(t) {
  for (const o of trucks) {
    if (o===t||o.status==='IDLE') continue;
    const dx=t.x-o.x, dy=t.y-o.y;
    if (dx*dx+dy*dy < COLL_DIST*COLL_DIST) return true;
  }
  return false;
}

function lerp3(wps, p) {
  const seg = p<0.33?0:p<0.66?1:2;
  const s0  = [0,0.33,0.66][seg], s1=[0.33,0.66,1.0][seg];
  const t   = (p-s0)/(s1-s0);
  const a=wps[seg],b=wps[seg+1];
  return [a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t];
}

function stepTruck(t) {
  if (collides(t)) {
    t.waiting=true; t.wt++;
    if (t.wt>10){t.waiting=false;t.wt=0;}
    return;
  }
  t.waiting=false; t.wt=0;

  if (t.status==='IDLE') {
    const cands = hexes.filter(h=>h.lane===t.lane&&!h.locked&&h.height<2.4);
    if (!cands.length) return;
    cands.sort((a,b)=>b.x-a.x);
    const tgt=cands[0]; tgt.locked=true;
    t.target=tgt; t.status='HAULING'; t.progress=0;
    t.wps=[[t.sx,t.sy],[t.sx,tgt.y-15],[tgt.x-TURN_R,tgt.y-15],[tgt.x,tgt.y]];

  } else if (t.status==='HAULING') {
    t.progress+=0.02;
    [t.x,t.y]=lerp3(t.wps,Math.min(t.progress,0.9999));
    if (t.progress>=1) {
      const g=t.target;
      g.height=Math.min(2.5,g.height+0.6); g.locked=false; g.dumps++;
      stats.tonnage+=400; stats.dumps++; t.loads++;
      t.status='RETURNING'; t.progress=0;
      t.wps=[[g.x,g.y],[g.x-TURN_R,g.y],[t.sx,g.y],[t.sx,t.sy]];
    }

  } else if (t.status==='RETURNING') {
    t.progress+=0.025;
    [t.x,t.y]=lerp3(t.wps,Math.min(t.progress,0.9999));
    if (t.progress>=1) {
      t.status='IDLE'; t.x=t.sx; t.y=t.sy; t.target=null;
    }
  }
}

function simStep() {
  for (const t of trucks) stepTruck(t);
}

// ══════════════════════════════════════════════════════════
// RENDERING
// ══════════════════════════════════════════════════════════
function hexPts(h) {
  const xs=[],ys=[];
  for(let i=0;i<6;i++){
    const a=Math.PI/180*(60*i+30);
    xs.push(h.x+HEX_R*Math.cos(a));
    ys.push(h.y+HEX_R*Math.sin(a));
  }
  xs.push(xs[0]);ys.push(ys[0]);
  return {xs,ys};
}

function hxColor(h) {
  if(h.locked)       return '#555';
  if(h.height>=2.4)  return '#cc0000';
  if(h.height>0.8)   return '#0055ff';
  return '#00cc44';
}

function tkColor(t) {
  if(t.waiting)              return '#ff6600';
  if(t.status==='HAULING')   return '#00ff00';
  if(t.status==='RETURNING') return '#ffcd00';
  return '#555';
}

function buildTraces() {
  const tr=[];
  for(const h of hexes){
    const {xs,ys}=hexPts(h);
    tr.push({x:xs,y:ys,type:'scatter',mode:'lines',fill:'toself',
             fillcolor:hxColor(h),line:{color:'#333',width:1},
             showlegend:false,hoverinfo:'text',
             hovertext:`Lane ${h.lane}<br>Height: ${h.height.toFixed(2)}m<br>Dumps: ${h.dumps}`});
  }
  for(const t of trucks){
    if(t.status!=='IDLE'&&t.target&&t.wps.length)
      tr.push({x:t.wps.map(w=>w[0]),y:t.wps.map(w=>w[1]),
               type:'scatter',mode:'lines',
               line:{color:'#ffcd00',width:1.5,dash:'dot'},
               showlegend:false,hoverinfo:'none'});
  }
  for(const t of trucks){
    // glow ring
    tr.push({x:[t.x],y:[t.y],type:'scatter',mode:'markers',
             marker:{symbol:'square',size:32,color:'rgba(255,205,0,0.15)',
                     line:{color:tkColor(t),width:2}},
             showlegend:false,hoverinfo:'none'});
    // truck body
    tr.push({x:[t.x],y:[t.y],type:'scatter',mode:'markers+text',
             marker:{symbol:'square',size:26,color:'#ffcd00',
                     line:{color:tkColor(t),width:3}},
             text:[t.id.split('-')[1]],
             textfont:{color:'#000',size:9,family:'Arial Black'},
             textposition:'middle center',showlegend:false,
             hoverinfo:'text',
             hovertext:`<b>${t.id}</b><br>Status: ${t.status}${t.waiting?' (WAITING)':''}<br>Loads: ${t.loads}<br>Lane: ${t.lane}`});
  }
  return tr;
}

const LAYOUT={
  xaxis:{showgrid:false,zeroline:false,fixedrange:true,showticklabels:false,
         scaleanchor:'y',scaleratio:1,range:[200,950]},
  yaxis:{showgrid:false,zeroline:false,fixedrange:true,showticklabels:false,range:[0,650]},
  plot_bgcolor:'rgba(0,0,0,0)', paper_bgcolor:'rgba(0,0,0,0)',
  margin:{l:0,r:0,t:0,b:0}, height:480, dragmode:false,
  uirevision:'static',
  annotations:[{
    x:.95,y:.5,xref:'paper',yref:'paper',
    text:'⬅️ FILLING DIRECTION',showarrow:true,arrowhead:2,
    arrowsize:1.5,arrowcolor:'#ffcd00',arrowwidth:3,
    font:{color:'#ffcd00',size:13,family:'Arial Black'},
    bgcolor:'rgba(0,0,0,.7)'
  }]
};
const CFG={displayModeBar:false,responsive:true};

function renderFrame() {
  const traces=buildTraces();
  if(!plotInited){
    Plotly.newPlot('map',traces,LAYOUT,CFG);
    plotInited=true;
  } else {
    Plotly.react('map',traces,LAYOUT,CFG);
  }
  updateUI();
}

function updateUI() {
  const filled  = hexes.filter(h=>h.height>=2.4).length;
  const total   = hexes.length;
  const pct     = total>0?(filled/total*100).toFixed(1):0;
  const active  = trucks.filter(t=>t.status!=='IDLE').length;
  const waiting = trucks.filter(t=>t.waiting).length;
  const rzone   = hexes.filter(h=>h.height<2.4&&h.x>700).length;
  const spd     = document.getElementById('cfg-speed').value;

  // stat boxes
  document.getElementById('s-tonnage').textContent = stats.tonnage.toLocaleString();
  document.getElementById('s-dumps').textContent   = stats.dumps;

  // metrics
  document.getElementById('m-rzone').textContent = rzone;
  document.getElementById('m-live').textContent  = active;
  document.getElementById('m-safe').textContent  = waiting;

  // fleet status badge
  const fsEl = document.getElementById('fleet-status');
  if(running){ fsEl.textContent='🔥 COLLISION AVOIDANCE ACTIVE'; fsEl.style.color='#00cc44'; }
  else        { fsEl.textContent='⏸️ PAUSED';                    fsEl.style.color='#ffcd00'; }

  // progress
  document.getElementById('prog-bar').style.width = pct+'%';
  document.getElementById('prog-label').textContent = `${filled} / ${total} (${pct}%)`;

  // fleet table
  const tbody = document.getElementById('fleet-body');
  tbody.innerHTML = trucks.map(t=>{
    let st='⚪ IDLE';
    if(t.status==='HAULING')   st='🟡 HAULING → RIGHT';
    else if(t.status==='RETURNING') st='🟢 RETURNING';
    else if(t.waiting)         st='🟠 WAITING';
    return `<tr><td>${t.id}</td><td>${st}</td><td>${t.loads}</td><td>${t.lane}</td></tr>`;
  }).join('');

  // status bar
  document.getElementById('statusbar').textContent =
    `🔄 Update: ${spd}ms | Safe turn radius: 25px | Collision dist: 35px | ${filled}/${total} cells filled`;
}

// ══════════════════════════════════════════════════════════
// BUTTON HANDLERS
// ══════════════════════════════════════════════════════════
function handleStart() {
  if(simTimer) clearInterval(simTimer);
  plotInited=false;
  initSim();

  // show map, hide splash
  document.getElementById('splash').style.display='none';
  document.getElementById('map').style.display='block';

  running=true;
  setButtons('running');
  renderFrame();

  const ms = parseInt(document.getElementById('cfg-speed').value)||300;
  simTimer = setInterval(()=>{ simStep(); renderFrame(); }, ms);
  document.getElementById('statusbar').textContent='✅ Running…';
}

function handleStop() {
  if(simTimer){ clearInterval(simTimer); simTimer=null; }
  running=false;
  setButtons('paused');
  updateUI();
}

function handleReset() {
  if(simTimer){ clearInterval(simTimer); simTimer=null; }
  running=false; plotInited=false;
  hexes=[]; trucks=[]; stats={tonnage:0,dumps:0};

  // show splash again
  document.getElementById('map').style.display='none';
  document.getElementById('splash').style.display='flex';

  setButtons('idle');
  document.getElementById('s-tonnage').textContent='0';
  document.getElementById('s-dumps').textContent='0';
  document.getElementById('prog-bar').style.width='0%';
  document.getElementById('prog-label').textContent='0 / 0 (0.0%)';
  document.getElementById('fleet-body').innerHTML='';
  document.getElementById('m-rzone').textContent='—';
  document.getElementById('m-live').textContent='—';
  document.getElementById('m-safe').textContent='—';
  const fsEl=document.getElementById('fleet-status');
  fsEl.textContent='⚪ STANDBY'; fsEl.style.color='#888';
  document.getElementById('statusbar').textContent='⏳ Waiting for start…';
}

function setButtons(state) {
  const s=document.getElementById('btn-start');
  const p=document.getElementById('btn-stop');
  const r=document.getElementById('btn-reset');
  if(state==='running'){ s.disabled=true;  p.disabled=false; r.disabled=false; }
  if(state==='paused') { s.disabled=false; p.disabled=true;  r.disabled=false; }
  if(state==='idle')   { s.disabled=false; p.disabled=true;  r.disabled=true;  }
}
</script>
</body>
</html>"""

components.html(HTML, height=780, scrolling=False)
