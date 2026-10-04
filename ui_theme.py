import streamlit as st

THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --brand:#23869b; --brand-dark:#1b6f82; --brand-2:#2bb3a0;
  --brand-soft:rgba(35,134,155,.10); --hero-a:#ebf7f7;
  --ink:#1d2730; --muted:#6b7885; --line:#e5eaed; --surface:#ffffff; --bg:#fafafc;
  --success:#16845b; --warning:#b7791f; --danger:#c23b3b;
  --shadow:0 4px 18px rgba(30,60,80,.07);
  --shadow-hover:0 10px 28px rgba(35,134,155,.16);
  --grad:linear-gradient(135deg,var(--brand),var(--brand-2));
}
html, body, .stApp, button, input, textarea, select { font-family:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif !important; }
.stApp { background:linear-gradient(180deg,var(--hero-a) 0,var(--bg) 340px); color:var(--ink); }
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] { display:none !important; }
header[data-testid="stHeader"] { background:transparent; }
.block-container { padding-top:2rem; padding-bottom:3rem; max-width:1400px; }

@keyframes fadeUp { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:none; } }
@keyframes pulseDot { 0%,100% { box-shadow:0 0 0 0 rgba(35,134,155,.45); } 70% { box-shadow:0 0 0 7px rgba(35,134,155,0); } }
@keyframes shimmer { from { background-position:-200% 0; } to { background-position:200% 0; } }
.block-container > div > div { animation:fadeUp .45s ease both; }
.finding, .card, .metric, .scope-item, .plan-row, .timeline-row { animation:fadeUp .45s ease both; }

[data-testid="stSidebar"] { background:var(--surface); border-right:1px solid var(--line); }
[data-testid="stSidebar"] > div:first-child { padding:1.2rem 1rem; }
.brand { display:flex; align-items:center; gap:12px; font-size:20px; font-weight:800; letter-spacing:-.3px; color:var(--ink); padding:4px 6px 18px; }
.brand-mark { color:var(--brand); }

.brand-tile { width:42px; height:42px; border-radius:12px; background:var(--grad); display:grid; place-items:center; box-shadow:0 6px 14px rgba(35,134,155,.28); flex:none; }
.brand-tile svg { stroke:#fff; }
.workspace-box { border:1px solid var(--line); border-radius:12px; padding:13px 14px; background:#fff; box-shadow:var(--shadow); transition:box-shadow .2s ease, transform .2s ease; }
.workspace-box:hover { box-shadow:var(--shadow-hover); transform:translateY(-1px); }
.nav-caption { color:#8a949d; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.08em; margin:10px 6px 5px; }
[data-testid="stSidebar"] [role="radiogroup"] { gap:4px; }
[data-testid="stSidebar"] [role="radiogroup"] label { position:relative; padding:11px 14px; border-radius:12px; color:var(--muted); font-weight:600; cursor:pointer; transition:background .18s ease, color .18s ease, transform .18s ease; }
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child { display:none; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background:var(--brand-soft); color:var(--brand-dark); transform:translateX(2px); }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) { background:var(--brand-soft); color:var(--brand); box-shadow:inset 4px 0 0 var(--brand); }

.page-kicker { color:var(--brand); font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.1em; margin-bottom:6px; }
.page-title { font-size:32px; line-height:1.15; font-weight:800; letter-spacing:-.5px; color:var(--ink); margin-bottom:6px; }
.page-subtitle { color:var(--muted); font-size:15px; margin-bottom:24px; }

.card { background:var(--surface); border:1px solid var(--line); border-radius:16px; padding:22px; box-shadow:var(--shadow); transition:box-shadow .22s ease, transform .22s ease; }
.card:hover { box-shadow:var(--shadow-hover); transform:translateY(-2px); }
.card + .card { margin-top:16px; }
.card-title { font-size:18px; font-weight:700; margin-bottom:5px; }
.card-subtitle { color:var(--muted); font-size:13px; line-height:1.55; }
.metric { background:var(--surface); border:1px solid var(--line); border-radius:16px; padding:18px; min-height:108px; box-shadow:var(--shadow); transition:box-shadow .22s ease, transform .22s ease; }
.metric:hover { box-shadow:var(--shadow-hover); transform:translateY(-2px); }
.metric-label { color:var(--muted); font-size:13px; font-weight:600; }
.metric-value { font-size:28px; font-weight:800; margin-top:7px; }
.metric-note { color:#8a949d; font-size:12px; margin-top:4px; }

.stepper { display:flex; gap:0; margin:0 0 20px; }
.step { flex:1; position:relative; padding:12px 8px; text-align:center; border-bottom:3px solid #dfe6ea; color:#87929b; font-size:12px; transition:color .2s ease, border-color .2s ease; }
.step.active { color:var(--brand-dark); border-bottom-color:var(--brand); font-weight:700; }
.step.done { color:var(--success); border-bottom-color:#9ed7c1; }
.step-num { display:inline-flex; width:24px; height:24px; align-items:center; justify-content:center; border-radius:50%; background:#edf2f4; margin-right:5px; font-weight:700; }
.step.active .step-num { background:var(--grad); color:white; animation:pulseDot 1.8s infinite; }

.step.done .step-num { background:#dff3ea; color:var(--success); }

.scope-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-top:15px; }
.scope-item { border:1px solid var(--line); border-radius:14px; padding:14px; background:#fff; transition:transform .2s ease, box-shadow .2s ease, border-color .2s ease; }
.scope-item:hover { transform:translateY(-2px); box-shadow:var(--shadow-hover); }
.scope-item.selected { border-color:var(--brand); background:var(--brand-soft); }
.scope-name { font-weight:700; font-size:14px; }
.scope-note { font-size:11px; color:var(--muted); margin-top:3px; }
.plan-row { display:flex; align-items:center; gap:10px; padding:12px 0; border-bottom:1px solid #eef2f4; }
.plan-row:last-child { border-bottom:0; }
.plan-node { width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center; background:var(--grad); color:#fff; font-weight:750; font-size:12px; }
.plan-arrow { color:#a0aab2; }

.status { display:inline-block; border-radius:999px; padding:4px 10px; font-size:11px; font-weight:700; }
.status-running { background:#e3f2f5; color:var(--brand-dark); background-image:linear-gradient(90deg,transparent,rgba(255,255,255,.7),transparent); background-size:200% 100%; animation:shimmer 1.8s linear infinite; }
.status-review { background:#fff5df; color:#95620d; }
.status-complete { background:#e5f5ee; color:var(--success); }
.status-danger { background:#fdecec; color:var(--danger); }
.status-neutral { background:#eef2f4; color:#66737c; }

.finding { border:1px solid var(--line); border-radius:16px; padding:18px; background:#fff; margin-bottom:12px; box-shadow:var(--shadow); transition:box-shadow .22s ease, transform .22s ease; }
.finding:hover { box-shadow:var(--shadow-hover); transform:translateY(-2px); }
.finding.high { border-left:4px solid var(--danger); }
.finding.medium { border-left:4px solid var(--warning); }
.finding.low { border-left:4px solid #7d8b94; }
.finding-id { font-weight:750; }
.finding-desc { margin-top:9px; line-height:1.55; }
.evidence { background:var(--bg); border:1px solid var(--line); border-radius:10px; padding:12px; margin-top:8px; }
.timeline-row { display:flex; gap:13px; padding:10px 0; }
.timeline-dot { width:10px; height:10px; border-radius:50%; background:var(--brand); margin-top:5px; flex:none; }
.timeline-title { font-weight:650; font-size:14px; }
.timeline-text { color:var(--muted); font-size:12px; margin-top:2px; }


.stButton > button { border-radius:10px; min-height:42px; font-weight:600; border:1px solid var(--brand); color:var(--brand); background:#fff; transition:transform .15s ease, box-shadow .15s ease, background .15s ease; }
.stButton > button:hover { background:var(--brand-soft); border-color:var(--brand); color:var(--brand-dark); transform:translateY(-1px); box-shadow:var(--shadow-hover); }
.stButton > button:active { transform:translateY(0); }
.stButton > button[kind="primary"] { background:var(--brand); border-color:var(--brand); color:#fff; }
.stButton > button[kind="primary"]:hover { background:var(--brand-dark); border-color:var(--brand-dark); color:#fff; }
[data-baseweb="select"] > div, .stTextInput input, .stTextArea textarea { border-radius:10px; }
.stTextInput input:focus, .stTextArea textarea:focus { border-color:var(--brand); box-shadow:0 0 0 3px var(--brand-soft); }
[data-testid="stMetric"] { background:#fff; border:1px solid var(--line); border-radius:14px; padding:12px; box-shadow:var(--shadow); }
[data-testid="stExpander"] { border:1px solid var(--line); border-radius:14px; background:#fff; box-shadow:var(--shadow); }
[data-testid="stAlert"] { border-radius:12px; }

@media (max-width:900px) { .scope-grid { grid-template-columns:repeat(2,1fr); } .page-title { font-size:26px; } }
@media (prefers-reduced-motion:reduce) { *, *::before, *::after { animation:none !important; transition:none !important; } }
</style>
"""

LOGO_SVG = (
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round">'
    '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>'
)

BRAND_HTML = f'<div class="brand"><span class="brand-tile">{LOGO_SVG}</span> SecureVDR</div>'


def apply_theme():
    st.markdown(THEME_CSS, unsafe_allow_html=True)
