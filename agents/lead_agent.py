"""
Lead DD Agent

Responsibilities:
1. Inspect documents available in the workspace.
2. Identify relevant DD areas.
3. Build the DD execution plan.
4. Select available specialist agents.
5. Route execution to the selected specialist agent.

Current specialist:
- financial

Future specialists:
- legal
- commercial
- tax
- hr
- compliance
"""

# -------------------------------------------------------------------
# Available specialist agents
# -------------------------------------------------------------------

AVAILABLE_AGENTS = {
    "financial": "classify",

    # Add these when the specialist agents are created:
    # "legal": "legal_start",
    # "commercial": "commercial_start",
    # "tax": "tax_start",
    # "hr": "hr_start",
    # "compliance": "compliance_start",
}


def register_agent(name, route):
    """A workstream registers itself with the Lead Agent.
    Existing entries are kept, so the old financial-only graph is unaffected."""

    AVAILABLE_AGENTS.setdefault(name, route)


# -------------------------------------------------------------------
# Document patterns
# -------------------------------------------------------------------

FINANCIAL_DOCUMENT_PATTERNS = [
    "income",
    "balance",
    "cash flow",
    "cashflow",
    "revenue",
    "profit",
    "financial",
    "p&l",
    "statement",
]

LEGAL_DOCUMENT_PATTERNS = [
    "agreement",
    "contract",
    "legal",
    "share purchase",
    "spa",
    "nda",
    "employment agreement",
    "lease",
    "litigation",
]

COMMERCIAL_DOCUMENT_PATTERNS = [
    "market",
    "customer",
    "sales",
    "commercial",
    "competitor",
    "business plan",
    "pipeline",
]


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _clean_requested(requested):
    """
    Normalize requested DD types.
    """

    return [
        str(item).strip().lower()
        for item in (requested or [])
        if str(item).strip()
    ]


def _document_names(state):
    """
    Extract document names from the graph state.
    """

    documents = state.get("documents") or []

    names = []

    for document in documents:

        if isinstance(document, dict):

            name = (
                document.get("document")
                or document.get("name")
                or document.get("filename")
            )

        else:
            name = str(document)

        if name:
            names.append(str(name))

    return names


def _contains_pattern(document_name, patterns):
    """
    Check whether a document name matches one of the
    known DD-area patterns.
    """

    name = document_name.lower()

    return any(
        pattern in name
        for pattern in patterns
    )


# -------------------------------------------------------------------
# Detect DD areas from documents
# -------------------------------------------------------------------

def detect_dd_types(document_names):
    """
    Detect DD areas based on the available workspace documents.

    This is deterministic for the current POC.
    """

    detected = []

    # Financial
    if any(
        _contains_pattern(
            name,
            FINANCIAL_DOCUMENT_PATTERNS
        )
        for name in document_names
    ):
        detected.append("financial")

    # Legal
    if any(
        _contains_pattern(
            name,
            LEGAL_DOCUMENT_PATTERNS
        )
        for name in document_names
    ):
        detected.append("legal")

    # Commercial
    if any(
        _contains_pattern(
            name,
            COMMERCIAL_DOCUMENT_PATTERNS
        )
        for name in document_names
    ):
        detected.append("commercial")

    return detected


# -------------------------------------------------------------------
# Build DD plan
# -------------------------------------------------------------------

def build_dd_plan(requested_types, detected_types):
    """
    Build the DD execution plan.

    Explicitly requested DD types take priority.

    If nothing was explicitly requested, use
    document-based detection.
    """

    requested = _clean_requested(requested_types)
    detected = _clean_requested(detected_types)

    if requested:
        candidates = requested
    else:
        candidates = detected

    plan = []

    for dd_type in candidates:

        if (
            dd_type in AVAILABLE_AGENTS
            and dd_type not in plan
        ):
            plan.append(dd_type)

    return plan


# -------------------------------------------------------------------
# Backward-compatible function
# -------------------------------------------------------------------

def plan_types(requested):
    """
    Validate requested DD types against available agents.

    This function is used by workflow.dd_graph.py.

    Example:

        plan_types(["financial"])

    returns:

        ["financial"]
    """

    requested_types = _clean_requested(requested)

    plan = []

    for dd_type in requested_types:

        if (
            dd_type in AVAILABLE_AGENTS
            and dd_type not in plan
        ):
            plan.append(dd_type)

    if not plan:

        raise ValueError(
            f"No available agent for: "
            f"{', '.join(requested_types) or 'none'}. "
            f"Available: "
            f"{', '.join(AVAILABLE_AGENTS)}."
        )

    return plan


# -------------------------------------------------------------------
# Lead Agent
# -------------------------------------------------------------------

def lead_node(state):
    """
    Main Lead Agent node.

    The Lead Agent:

    1. Looks at workspace documents.
    2. Detects relevant DD areas.
    3. Creates the execution plan.
    4. Selects available specialist agents.
    5. Provides the routing decision to LangGraph.
    """

    # ---------------------------------------------------------------
    # Read documents
    # ---------------------------------------------------------------

    document_names = _document_names(state)

    # ---------------------------------------------------------------
    # Read requested DD types
    # ---------------------------------------------------------------

    requested_types = _clean_requested(
        state.get("dd_types")
    )

    # ---------------------------------------------------------------
    # Detect DD areas
    # ---------------------------------------------------------------

    detected_types = detect_dd_types(
        document_names
    )

    # ---------------------------------------------------------------
    # Build execution plan
    # ---------------------------------------------------------------

    plan = build_dd_plan(
        requested_types,
        detected_types,
    )

    # ---------------------------------------------------------------
    # Default to financial for current POC
    # ---------------------------------------------------------------

    if (
        not plan
        and not requested_types
        and "financial" in AVAILABLE_AGENTS
    ):
        plan = ["financial"]

    # ---------------------------------------------------------------
    # Find unavailable specialist agents
    # ---------------------------------------------------------------

    requested_or_detected = (
        requested_types
        if requested_types
        else detected_types
    )

    skipped = [
        dd_type
        for dd_type in requested_or_detected
        if dd_type not in AVAILABLE_AGENTS
    ]

    # ---------------------------------------------------------------
    # Build Lead Agent notes
    # ---------------------------------------------------------------

    lead_notes = []

    lead_notes.append(
        f"{len(document_names)} document(s) available "
        f"in workspace"
    )

    if detected_types:

        lead_notes.append(
            "Detected DD areas: "
            + ", ".join(detected_types)
        )

    if plan:

        lead_notes.append(
            "Execution plan: "
            + " -> ".join(plan)
        )

    else:

        lead_notes.append(
            "No specialist agent selected"
        )

    for dd_type in skipped:

        lead_notes.append(
            f"'{dd_type}' specialist agent "
            f"is not available yet"
        )

    # ---------------------------------------------------------------
    # Console output
    # ---------------------------------------------------------------

    print("\n" + "=" * 60)
    print("[Lead Agent] DD planning started")
    print("=" * 60)

    print("\n[Lead Agent] Workspace documents:")

    for name in document_names:

        print(f"  - {name}")

    print(
        "\n[Lead Agent] Requested DD types: "
        f"{requested_types or 'none'}"
    )

    print(
        "[Lead Agent] Detected DD types: "
        f"{detected_types or 'none'}"
    )

    print(
        "[Lead Agent] Selected agents: "
        f"{plan or 'none'}"
    )

    print(
        "[Lead Agent] Execution plan: "
        f"{' -> '.join(plan) if plan else 'none'}"
    )

    if skipped:

        print(
            "\n[Lead Agent] Specialists not available yet:"
        )

        for dd_type in skipped:

            print(f"  - {dd_type}")

    print("\n[Lead Agent] Planning complete")
    print("=" * 60)

    # ---------------------------------------------------------------
    # Return state updates
    # ---------------------------------------------------------------

    return {
        "dd_types": (
            requested_types
            or detected_types
        ),

        "plan": plan,

        "required_agents": plan,

        "lead_notes": lead_notes,

        "lead_decision": {
            "documents_analyzed": document_names,
            "requested_types": requested_types,
            "detected_types": detected_types,
            "selected_agents": plan,
            "skipped_agents": skipped,
        },
    }


# -------------------------------------------------------------------
# LangGraph routing
# -------------------------------------------------------------------

def route_after_lead(state):
    """
    Route from the Lead Agent to the selected specialist.

    Current:

        financial -> classify

    Future:

        legal -> legal_start
        commercial -> commercial_start
    """

    plan = state.get("plan") or []

    if not plan:

        print(
            "\n[Lead Agent] No specialist selected. "
            "Routing to save."
        )

        return "save"

    first_agent = plan[0]

    route = AVAILABLE_AGENTS.get(
        first_agent
    )

    if route is None:

        print(
            f"\n[Lead Agent] No route found for "
            f"{first_agent}. Routing to save."
        )

        return "save"

    print(
        f"\n[Lead Agent] Routing to "
        f"{first_agent} agent -> {route}"
    )

    return route