"""Real model-driven DD planner with deterministic safety fallback."""
import json
from llm.gateway import generate_agent
from llm.schemas import InvestigationPlan

AVAILABLE_AGENTS = {"financial": "financial_ws", "legal": "legal_ws"}
FINANCIAL_DOCUMENT_PATTERNS = ["income","balance","cash flow","cashflow","revenue","profit","financial","p&l","statement"]
LEGAL_DOCUMENT_PATTERNS = ["agreement","contract","legal","share purchase","spa","nda","employment agreement","lease","litigation"]

def register_agent(name: str, route: str) -> None: AVAILABLE_AGENTS.setdefault(name, route)
def _clean_requested(requested): return [str(x).strip().lower() for x in (requested or []) if str(x).strip()]
def _document_names(state):
    names=[]
    for document in state.get("documents") or []:
        name=(document.get("document") or document.get("name") or document.get("filename")) if isinstance(document,dict) else str(document)
        if name: names.append(str(name))
    return names

def detect_dd_types(document_names):
    detected=[]
    if any(any(p in n.lower() for p in FINANCIAL_DOCUMENT_PATTERNS) for n in document_names): detected.append("financial")
    if any(any(p in n.lower() for p in LEGAL_DOCUMENT_PATTERNS) for n in document_names): detected.append("legal")
    return detected

def build_dd_plan(requested_types, detected_types):
    return list(dict.fromkeys(x for x in (_clean_requested(requested_types) or _clean_requested(detected_types)) if x in AVAILABLE_AGENTS))

def plan_types(requested):
    plan=list(dict.fromkeys(x for x in _clean_requested(requested) if x in AVAILABLE_AGENTS))
    if not plan: raise ValueError(f"No available agent for: {', '.join(_clean_requested(requested)) or 'none'}. Available: {', '.join(AVAILABLE_AGENTS)}.")
    return plan

def _fallback_plan(names, requested):
    candidates=_clean_requested(requested) or detect_dd_types(names) or ["financial"]
    tasks=[]
    for ws in candidates:
        if ws not in AVAILABLE_AGENTS: continue
        patterns=FINANCIAL_DOCUMENT_PATTERNS if ws=="financial" else LEGAL_DOCUMENT_PATTERNS
        tasks.append({"workstream":ws,"task":f"Perform {ws} due diligence review using the available documents.","reason":"Planner unavailable; deterministic fallback.","priority":"MEDIUM","evidence_documents":[n for n in names if any(p in n.lower() for p in patterns)]})
    return {"summary":"Fallback plan generated from document inventory.","tasks":tasks}

def lead_node(state):
    names=_document_names(state); requested=_clean_requested(state.get("dd_types"))
    prompt=f"Create a due-diligence investigation plan from this workspace inventory. Only select Financial or Legal. Do not invent documents. Return JSON matching this schema: {json.dumps(InvestigationPlan.model_json_schema())}. Documents: {json.dumps(names)}. Requested workstreams: {json.dumps(requested)}"
    try:
        raw=generate_agent(prompt,system="You are a cautious DD planner. Use only supplied document names.",format=InvestigationPlan.model_json_schema())
        plan=InvestigationPlan.model_validate_json(raw)
        selected=[]
        for task in plan.tasks:
            if task.workstream in AVAILABLE_AGENTS and task.workstream not in selected: selected.append(task.workstream)
        if requested: selected=[x for x in selected if x in requested]
        if not selected: raise ValueError("Planner returned no usable workstream")
        return {"dd_types":requested or selected,"plan":selected,"required_agents":selected,"lead_notes":[plan.summary]+[t.task for t in plan.tasks],"lead_decision":{"documents_analyzed":names,"requested_types":requested,"selected_agents":selected,"planner_fallback":False},"investigation_plan":plan.model_dump()}
    except Exception as exc:
        fallback=_fallback_plan(names,requested); selected=[t["workstream"] for t in fallback["tasks"]]
        return {"dd_types":requested or selected,"plan":selected,"required_agents":selected,"lead_notes":[fallback["summary"],f"Planner fallback: {type(exc).__name__}"],"lead_decision":{"documents_analyzed":names,"requested_types":requested,"selected_agents":selected,"planner_fallback":True},"investigation_plan":fallback}

def route_after_lead(state):
    plan=state.get("plan") or []
    return AVAILABLE_AGENTS.get(plan[0],"save") if plan else "save"
