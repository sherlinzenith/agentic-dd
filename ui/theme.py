"""SecureVDR look & feel. Edit the colours in the :root block only."""

import html

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{
 --brand:#23869b; --brand-dark:#1b6f82; --brand-2:#2bb3a0; --soft:rgba(35,134,155,.10);
 --hero:#ebf7f7; --ink:#1d2730; --muted:#6b7885; --line:#e5eaed; --bg:#fafafc; --surface:#fff;
 --ok:#16845b; --okb:#e5f5ee; --warn:#b7791f; --warnb:#fff5df; --bad:#c23b3b; --badb:#fdecec;
 --shadow:0 4px 18px rgba(30,60,80,.07); --lift:0 10px 28px rgba(35,134,155,.16);
 --grad:linear-gradient(135deg,var(--brand),var(--brand-2));
}
html,body,.stApp,button,input,textarea,select{font-family:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif!important}
.stApp{background:linear-gradient(180deg,var(--hero) 0,var(--bg) 320px);color:var(--ink)}
#MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
header[data-testid="stHeader"]{background:transparent}
.block-container{padding:2rem 2.6rem 4rem;max-width:1380px}
@keyframes up{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(35,134,155,.45)}70%{box-shadow:0 0 0 8px rgba(35,134,155,0)}}
@keyframes shimmer{from{background-position:-200% 0}to{background-position:200% 0}}
.card,.metric,.finding,.doc-row,.step,.tl{animation:up .4s ease both}

/* sidebar */
[data-testid="stSidebar"]{background:var(--surface);border-right:1px solid var(--line)}
[data-testid="stSidebar"]>div:first-child{padding:1.3rem 1rem}
.brand{display:flex;align-items:center;gap:12px;font-size:20px;font-weight:800;letter-spacing:-.3px;padding:2px 6px 18px}
.brand-tile{width:42px;height:42px;border-radius:12px;background:var(--grad);display:grid;place-items:center;box-shadow:0 6px 14px rgba(35,134,155,.28);flex:none}
.brand-tile svg{stroke:#fff}
.wsbox{border:1px solid var(--line);border-radius:12px;padding:12px 14px;background:#fff;margin-bottom:14px}
.wsbox small{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.08em;font-weight:600}
.wsbox b{display:block;margin-top:2px;font-size:14px}
[data-testid="stSidebar"] [role="radiogroup"]{gap:4px}
[data-testid="stSidebar"] [role="radiogroup"] label{padding:11px 14px;border-radius:12px;color:var(--muted);font-weight:600;cursor:pointer;transition:background .18s,color .18s,transform .18s}
[data-testid="stSidebar"] [role="radiogroup"] label>div:first-child{display:none}
[data-testid="stSidebar"] [role="radiogroup"] label:hover{background:var(--soft);color:var(--brand-dark);transform:translateX(2px)}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){background:var(--soft);color:var(--brand);box-shadow:inset 4px 0 0 var(--brand)}

/* headings */
.kicker{color:var(--brand);font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;margin-bottom:6px}
.title{font-size:32px;line-height:1.15;font-weight:800;letter-spacing:-.5px;margin:0 0 6px}
.sub{color:var(--muted);font-size:15px;margin:0 0 22px;max-width:760px}

/* cards */
.card{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:20px 22px;box-shadow:var(--shadow);margin-bottom:14px;transition:box-shadow .2s,transform .2s}
.card:hover{box-shadow:var(--lift);transform:translateY(-1px)}
.card-h{font-size:17px;font-weight:700;margin-bottom:4px}.card-p{color:var(--muted);font-size:13px;line-height:1.55}
.metric{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:16px 18px;box-shadow:var(--shadow);min-height:96px;transition:box-shadow .2s,transform .2s}
.metric:hover{box-shadow:var(--lift);transform:translateY(-2px)}
.metric small{color:var(--muted);font-size:12px;font-weight:600}.metric b{display:block;font-size:28px;font-weight:800;margin-top:6px}
.metric i{color:#8a949d;font-size:12px;font-style:normal}

/* stepper */
.stepper{display:flex;margin:0 0 22px}
.step{flex:1;text-align:center;padding:12px 6px;border-bottom:3px solid #dfe6ea;color:#87929b;font-size:12px;font-weight:600}
.step.done{color:var(--ok);border-color:#9ed7c1}.step.now{color:var(--brand-dark);border-color:var(--brand)}
.step span{display:inline-grid;place-items:center;width:24px;height:24px;border-radius:50%;background:#edf2f4;margin-right:6px;font-size:11px}
.step.done span{background:#dff3ea;color:var(--ok)}.step.now span{background:var(--grad);color:#fff;animation:pulse 1.8s infinite}

/* badges */
.badge{display:inline-block;border-radius:999px;padding:3px 10px;font-size:11px;font-weight:700;background:#eef2f4;color:#66737c;margin-left:4px;white-space:nowrap}
.b-brand{background:#e3f2f5;color:var(--brand-dark)}.b-ok{background:var(--okb);color:var(--ok)}
.b-warn{background:var(--warnb);color:#95620d}.b-bad{background:var(--badb);color:var(--bad)}
.b-run{background:#e3f2f5;color:var(--brand-dark);background-image:linear-gradient(90deg,transparent,rgba(255,255,255,.7),transparent);background-size:200% 100%;animation:shimmer 1.8s linear infinite}

/* rows */
.doc-row{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:12px 0;border-bottom:1px solid #eef2f4}
.doc-row:last-child{border-bottom:0}.doc-name{font-weight:600;font-size:14px}.doc-meta{color:var(--muted);font-size:12px;margin-top:2px}
.tl{display:flex;gap:14px;padding:10px 0}.tl-dot{width:10px;height:10px;border-radius:50%;background:var(--brand);margin-top:6px;flex:none}
.tl-t{font-weight:600;font-size:14px}.tl-d{color:var(--muted);font-size:12px;margin-top:2px}.tl-at{color:#8a949d;font-size:11px;margin-top:2px}

/* findings + evidence */
.finding{background:#fff;border:1px solid var(--line);border-left:4px solid #7d8b94;border-radius:16px;padding:18px 20px;box-shadow:var(--shadow);margin-bottom:12px}
.finding.high{border-left-color:var(--bad)}.finding.medium{border-left-color:var(--warn)}
.f-id{color:var(--muted);font-size:12px;font-weight:600}.f-title{font-size:19px;font-weight:700;margin:2px 0 8px}
.f-sec{margin-top:12px}.f-sec b{display:block;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:3px}
.evidence{background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin-top:8px;font-size:13px}
.evidence q{display:block;color:#4f5b64;margin-top:4px;quotes:none}
.pageview{background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px;font-size:13px;white-space:pre-wrap;line-height:1.6;max-height:300px;overflow:auto}
mark{background:#fff0b3;padding:1px 3px;border-radius:4px}

/* widgets */
.stButton>button{border-radius:10px;min-height:42px;font-weight:600;border:1px solid var(--brand);color:var(--brand);background:#fff;transition:transform .15s,box-shadow .15s,background .15s}
.stButton>button:hover{background:var(--soft);color:var(--brand-dark);transform:translateY(-1px);box-shadow:var(--lift)}
.stButton>button[kind="primary"]{background:var(--brand);color:#fff}.stButton>button[kind="primary"]:hover{background:var(--brand-dark);color:#fff}
.stButton>button:disabled{opacity:.45;transform:none;box-shadow:none}
[data-testid="stFileUploader"] section{border:1.5px dashed #b8c9cf;border-radius:14px;background:#fff}
[data-baseweb="select"]>div,.stTextInput input,.stTextArea textarea{border-radius:10px}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:var(--brand);box-shadow:0 0 0 3px var(--soft)}
[data-testid="stTabs"] [role="tab"]{font-weight:600}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
</style>
"""

LOGO = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round">'
        '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>')


def apply_theme():
    st.markdown(CSS, unsafe_allow_html=True)


def esc(x):
    return html.escape(str(x))


def brand():
    st.sidebar.markdown(f'<div class="brand"><span class="brand-tile">{LOGO}</span>SecureVDR</div>', unsafe_allow_html=True)


def header(kicker, title, sub=""):
    st.markdown(f'<div class="kicker">{esc(kicker)}</div><h1 class="title">{esc(title)}</h1><p class="sub">{esc(sub)}</p>', unsafe_allow_html=True)


def metric(col, label, value, note=""):
    col.markdown(f'<div class="metric"><small>{esc(label)}</small><b>{esc(value)}</b><i>{esc(note)}</i></div>', unsafe_allow_html=True)


def badge(text, kind=""):
    return f'<span class="badge {kind}">{esc(text)}</span>'


def card(title, body="", extra=""):
    st.markdown(f'<div class="card"><div class="card-h">{esc(title)}</div><div class="card-p">{body}</div>{extra}</div>', unsafe_allow_html=True)


def stepper(steps):
    """steps = [(label, state)] with state in done / now / todo"""
    inner = "".join(f'<div class="step {s}"><span>{"✓" if s == "done" else i}</span>{esc(l)}</div>' for i, (l, s) in enumerate(steps, 1))
    st.markdown(f'<div class="stepper">{inner}</div>', unsafe_allow_html=True)
