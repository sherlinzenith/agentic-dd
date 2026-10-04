"""Deterministic legal clause detection with page-level evidence.

No LLM here: a clause is only reported if its exact sentence is found
on a real page of a real document (verify_quote).
"""

import re

# id, label, severity, regex patterns, why it matters
CLAUSE_RULES = [
    {
        "id": "change_of_control",
        "label": "Change of Control",
        "severity": "HIGH",
        "patterns": [r"change of control", r"change in control"],
        "impact": "A change in ownership may give the counterparty rights to terminate, consent or renegotiate.",
    },
    {
        "id": "uncapped_liability",
        "label": "Uncapped Liability",
        "severity": "HIGH",
        "patterns": [r"unlimited liability", r"no (?:limit|cap) on (?:the )?liability"],
        "impact": "Liability under this contract may not be capped.",
    },
    {
        "id": "termination_convenience",
        "label": "Termination for Convenience",
        "severity": "MEDIUM",
        "patterns": [r"terminat\w*[^.;]{0,120}\bconvenience\b", r"terminat\w*[^.;]{0,80}without cause"],
        "impact": "A party can end the contract without cause, which affects revenue or supply stability.",
    },
    {
        "id": "assignment",
        "label": "Assignment Restriction",
        "severity": "MEDIUM",
        "patterns": [r"\bassign\w*[^.;]{0,120}\bconsent\b", r"\bconsent\b[^.;]{0,120}\bassign\w*"],
        "impact": "The contract cannot be transferred without consent, which matters in an acquisition.",
    },
    {
        "id": "exclusivity",
        "label": "Exclusivity / Non-compete",
        "severity": "MEDIUM",
        "patterns": [
            r"exclusive (?:supplier|distributor|rights?|dealing|arrangement|basis)",
            r"sole and exclusive",
            r"non-?compete",
        ],
        "impact": "Business activity may be restricted by exclusivity or non-compete terms.",
    },
    {
        "id": "auto_renewal",
        "label": "Auto-renewal",
        "severity": "LOW",
        "patterns": [r"automatically renew\w*", r"auto-?renew\w*"],
        "impact": "The contract renews unless notice is given, which affects commitment length.",
    },
]

# Standard clauses that should exist in a contract.
EXPECTED_CLAUSES = [
    {"id": "governing_law", "label": "Governing Law",
     "pattern": r"governed by[^.;]{0,100}\blaws?\b"},
    {"id": "limitation_of_liability", "label": "Limitation of Liability",
     "pattern": r"limitation of liability|liability[^.;]{0,80}shall not exceed|aggregate liability"},
]

CONTRACT_WORDS = ("agreement", "contract", "lease", "deed", "memorandum of understanding")

MAX_QUOTES_PER_CLAUSE = 3
MAX_QUOTE_CHARS = 300


def _norm(text):
    return re.sub(r"\s+", " ", text or "").strip()


def is_contract(document):
    text = (document.get("text") or "").lower()
    head = " ".join(text.splitlines()[:8])

    if any(word in head for word in CONTRACT_WORDS):
        return True

    return "governed by" in text and ("party" in text or "parties" in text)


def contract_title(document):
    for line in (document.get("text") or "").splitlines():
        if line.strip():
            return line.strip()
    return document.get("document", "")


def _sentences(page_text):
    flat = _norm(page_text)
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", flat) if s.strip()]


def verify_quote(quote, page_text):
    """True only if the quote really appears on that page."""
    return bool(quote) and _norm(quote) in _norm(page_text)


def extract_clauses(document):
    """Risk clauses found in one contract. One hit = one sentence on one page."""

    hits = []
    counts = {}

    for page_no, page_text in enumerate(document.get("pages") or [], start=1):

        for sentence in _sentences(page_text):

            for rule in CLAUSE_RULES:

                if counts.get(rule["id"], 0) >= MAX_QUOTES_PER_CLAUSE:
                    continue

                if any(re.search(p, sentence, re.IGNORECASE) for p in rule["patterns"]):

                    quote = sentence[:MAX_QUOTE_CHARS]

                    if not verify_quote(quote, page_text):
                        continue

                    counts[rule["id"]] = counts.get(rule["id"], 0) + 1

                    hits.append({
                        "clause_id": rule["id"],
                        "label": rule["label"],
                        "severity": rule["severity"],
                        "impact": rule["impact"],
                        "document": document["document"],
                        "page": page_no,
                        "quote": quote,
                    })

    return hits


def missing_clauses(document):
    """Standard clauses that were not found anywhere in the contract."""

    text = _norm(document.get("text") or "")

    return [
        {"clause_id": c["id"], "label": c["label"], "document": document["document"]}
        for c in EXPECTED_CLAUSES
        if not re.search(c["pattern"], text, re.IGNORECASE)
    ]