from .agent import CrossDomainAgent
from .prompts import CROSS_DOMAIN_AGENT_SYSTEM_PROMPT
from .tools import CrossDomainAgentTools
from workflow.activity import log

RULES = [
    {
        "id": "revenue_change_of_control",
        "financial": "Revenue",
        "legal": "Change of Control",
        "title": "Revenue figures and a change-of-control clause need joint review",
        "severity": "HIGH",
        "impact": "If revenue under this contract is relied on, an ownership change could affect it.",
    },
    {
        "id": "revenue_termination",
        "financial": "Revenue",
        "legal": "Termination for Convenience",
        "title": "Revenue figures and a termination-for-convenience right need joint review",
        "severity": "MEDIUM",
        "impact": "A contract that can be ended without cause may affect the stability of reported revenue.",
    },
]


def _legal_document(finding):
    ev = finding.get("evidence") or []
    return ev[0]["document"] if ev else "a contract"


def cross_domain_node(state):
    findings = list(state.get("findings") or [])

    financial = [f for f in findings if f.get("workstream") == "financial"]
    legal = [f for f in findings if f.get("workstream") == "legal"]

    cross = []

    for rule in RULES:
        fin = next((f for f in financial if f.get("category") == rule["financial"]), None)
        if not fin:
            continue

        for leg in (f for f in legal if f.get("category") == rule["legal"]):
            description = (
                f"{fin['finding_id']} ({fin['description']}) and {leg['finding_id']} "
                f"({rule['legal']} clause in {_legal_document(leg)}) should be reviewed together."
            )

            cross.append({
                "finding_id": f"CRS-{len(cross) + 1:03d}",
                "type": "CROSS_DOMAIN",
                "workstream": "cross_domain",
                "category": "Cross-Domain",
                "severity": rule["severity"],
                "status": "REVIEW_REQUIRED",
                "description": description,
                "impact": rule["impact"],
                "related_findings": [fin["finding_id"], leg["finding_id"]],
                "evidence": list(fin.get("evidence") or []) + list(leg.get("evidence") or []),
                "job_id": fin.get("job_id"),
                "ai_reasoning": {
                    "issue": rule["title"],
                    "why_it_matters": rule["impact"],
                    "what_should_be_reviewed": f"Review {fin['finding_id']} and {leg['finding_id']} together.",
                    "evidence_conclusion": "Both findings are supported by the evidence listed; their link is a review prompt, not a conclusion.",
                },
                "evidence_guard": {"status": "NOT_REQUIRED", "issues": []},
            })

    print(f"\n[Cross-domain] {len(cross)} cross-domain finding(s)")

    return {
        "findings": findings + cross,
        "activity": [log("cross_domain", f"{len(cross)} cross-domain finding(s)")],
    }

__all__ = [
    "CrossDomainAgent",
    "CROSS_DOMAIN_AGENT_SYSTEM_PROMPT",
    "CrossDomainAgentTools",
    "cross_domain_node",
    "RULES",
]
