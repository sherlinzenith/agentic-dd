"""
DD orchestrator.

Flow:

START
  ↓
inventory
  ↓
readiness
  ↓
lead / investigation plan
  ↓
selected workstreams
  ├── Financial → Financial documents only
  └── Legal     → Legal documents only
  ↓
merge
  ↓
cross-domain analysis
  ↓
evidence verification
  ↓
save
  ↓
human review
  ├── approve
  ├── reject
  └── request more evidence
          ↓
      re-analysis
  ↓
final report
"""

import operator
from typing import Annotated, Dict, List, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from findings import finding_store as store

from agents.financial_agent import (
    await_evidence_node,
    build_financial_subgraph,
    finish_node,
    review_node,
    route_after_review,
    save_node,
)

from agents.cross_domain import cross_domain_node
from agents.evidence_verify import verify_node
from agents.inventory import inventory_node
from agents.legal_agent import build_legal_subgraph
from agents.lead_agent import (
    lead_node,
    register_agent,
)
from agents.readiness import readiness_node
from workflow.activity import log


# ---------------------------------------------------------------
# Result merge
# ---------------------------------------------------------------

def merge_results(current, update):
    """
    Merge parallel workstream results.

    __reset__ is used when evidence is added and the analysis
    needs to be run again.
    """

    update = dict(update or {})

    reset = update.pop(
        "__reset__",
        False,
    )

    base = (
        {}
        if reset
        else dict(current or {})
    )

    base.update(update)

    return base


# ---------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------

class DDState(TypedDict, total=False):

    documents: List[Dict]

    dd_types: List[str]

    plan: List[str]

    required_agents: List[str]

    lead_notes: List[str]

    lead_decision: Dict

    results: Annotated[
        Dict[str, Dict],
        merge_results,
    ]

    findings: List[Dict]

    metrics: List[Dict]

    status: str

    overrides: Dict

    inventory: List[Dict]

    inventory_summary: Dict

    readiness: Dict

    activity: Annotated[
        List[Dict],
        operator.add,
    ]


# ---------------------------------------------------------------
# Workstreams
# ---------------------------------------------------------------

WORKSTREAMS = {
    "financial": (
        "financial_ws",
        build_financial_subgraph,
    ),

    "legal": (
        "legal_ws",
        build_legal_subgraph,
    ),
}


for _name, (
    _node,
    _builder,
) in WORKSTREAMS.items():

    register_agent(
        _name,
        _node,
    )


# ---------------------------------------------------------------
# Document routing
# ---------------------------------------------------------------

def _documents_for(
    name,
    state,
):
    """
    Return ONLY documents assigned to the requested workstream.

    Financial never receives Legal documents.
    Legal never receives Financial documents.

    If classification metadata is unavailable, we deliberately
    return an empty list rather than accidentally analyzing the
    entire workspace.
    """

    inventory = (
        state.get("inventory")
        or []
    )

    documents = (
        state.get("documents")
        or []
    )

    if not inventory:
        return []

    category_by_document = {}

    for row in inventory:

        document_name = row.get(
            "document"
        )

        category = row.get(
            "category"
        )

        if document_name and category:
            category_by_document[
                document_name
            ] = category

    scoped = []

    for document in documents:

        document_name = document.get(
            "document"
        )

        category = category_by_document.get(
            document_name
        )

        if category == name:
            scoped.append(document)

    return scoped


# ---------------------------------------------------------------
# Workstream node
# ---------------------------------------------------------------

def _workstream_node(
    name,
    subgraph,
):
    """
    Execute exactly one specialist workstream.

    The specialist receives only its own workspace documents.
    """

    def run(state):

        documents = (
            state.get("documents")
            or []
        )

        # -------------------------------------------------------
        # Safety guard
        # -------------------------------------------------------

        if not documents:

            message = (
                f"{name.title()} workstream skipped: "
                "no documents were assigned to this workstream."
            )

            print(
                f"\n[Workstream] {message}"
            )

            return {
                "results": {
                    name: {
                        "findings": [],
                        "metrics": [],
                        "notes": [
                            message
                        ],
                    }
                },

                "activity": [
                    log(
                        name,
                        message,
                    )
                ],
            }

        # -------------------------------------------------------
        # Run specialist
        # -------------------------------------------------------

        print(
            f"\n[{name.title()}] "
            f"Running on {len(documents)} document(s)..."
        )

        output = subgraph.invoke(
            {
                "documents": documents,
                "findings": [],
                "status": "STARTED",
            }
        )

        findings = []

        for finding in output.get(
            "findings",
            [],
        ):

            finding_copy = {
                **finding,
                "workstream": name,
            }

            findings.append(
                finding_copy
            )

        metrics = output.get(
            "metrics",
            [],
        )

        notes = output.get(
            "notes",
            [],
        )

        return {
            "results": {
                name: {
                    "findings": findings,
                    "metrics": metrics,
                    "notes": notes,
                }
            },

            "activity": [
                log(
                    name,
                    (
                        f"Completed. "
                        f"{len(findings)} finding(s), "
                        f"{len(metrics)} metric(s)."
                    ),
                )
            ],
        }

    return run


# ---------------------------------------------------------------
# Fan-out
# ---------------------------------------------------------------

def fan_out(state):
    """
    Dispatch both workstream nodes so that the merge barrier
    remains deterministic.

    Selected workstreams receive their classified documents.

    Unselected workstreams receive [] and immediately skip.

    This means:

        Financial only
             ↓
        Financial gets docs
        Legal gets []

    and:

        Legal only
             ↓
        Financial gets []
        Legal gets docs
    """

    selected = set(
        p
        for p in (
            state.get("plan")
            or []
        )
        if p in WORKSTREAMS
    )

    if not selected:

        print(
            "\n[Orchestrator] "
            "No workstreams selected."
        )

    sends = []

    for name, (
        node,
        _builder,
    ) in WORKSTREAMS.items():

        if name in selected:

            documents = _documents_for(
                name,
                state,
            )

            print(
                f"[Orchestrator] "
                f"{name}: "
                f"{len(documents)} document(s)"
            )

        else:

            documents = []

            print(
                f"[Orchestrator] "
                f"{name}: not selected"
            )

        sends.append(
            Send(
                node,
                {
                    "documents": documents,
                },
            )
        )

    return sends


# ---------------------------------------------------------------
# Job
# ---------------------------------------------------------------

def _job_id(config):

    return (
        (config or {})
        .get("configurable", {})
        .get("thread_id")
    )


def _scoped(fn):
    """
    Set the current findings-store job before executing a node.
    """

    def run(
        state,
        config: RunnableConfig,
    ):

        store.set_job(
            _job_id(config)
        )

        return fn(state)

    run.__name__ = fn.__name__

    return run


# ---------------------------------------------------------------
# Lead / planning
# ---------------------------------------------------------------

def lead_plan_node(state):
    """
    Lead Agent plans the investigation.

    It does not perform Financial or Legal analysis.
    """

    output = lead_node(
        state
    )

    plan = ", ".join(
        output.get("plan")
        or []
    ) or "none"

    output["activity"] = [
        log(
            "plan",
            f"Workstreams planned: {plan}",
        )
    ]

    return output


# ---------------------------------------------------------------
# Merge specialist results
# ---------------------------------------------------------------

def merge_node(
    state,
    config: RunnableConfig,
):

    job_id = _job_id(
        config
    )

    results = (
        state.get("results")
        or {}
    )

    findings = []
    metrics = []

    for name in WORKSTREAMS:

        result = results.get(
            name
        )

        if not result:
            continue

        for finding in result.get(
            "findings",
            [],
        ):

            findings.append(
                {
                    **finding,
                    "job_id": job_id,
                }
            )

        metrics.extend(
            result.get(
                "metrics",
                [],
            )
        )

    print(
        f"\n[Merge] "
        f"{len(findings)} finding(s) "
        f"from {', '.join(results) or 'none'}"
    )

    return {
        "findings": findings,
        "metrics": metrics,
    }


# ---------------------------------------------------------------
# Re-analysis
# ---------------------------------------------------------------

def reset_for_reanalysis(
    state
):

    output = await_evidence_node(
        state
    )

    output["results"] = {
        "__reset__": True
    }

    return output


# ---------------------------------------------------------------
# Cross-domain guard
# ---------------------------------------------------------------

def cross_domain_guard(
    state
):
    """
    Cross-domain analysis is useful only when at least two
    workstreams actually participated.

    Financial-only or Legal-only DD should not manufacture
    cross-domain findings.
    """

    plan = [
        p
        for p in (
            state.get("plan")
            or []
        )
        if p in WORKSTREAMS
    ]

    if len(plan) < 2:

        print(
            "\n[Cross Domain] "
            "Skipped: fewer than two workstreams selected."
        )

        return {
            "findings": state.get(
                "findings",
                []
            ),

            "activity": [
                log(
                    "cross_domain",
                    "Skipped because only one workstream was selected.",
                )
            ],
        }

    return cross_domain_node(
        state
    )


# ---------------------------------------------------------------
# Graph
# ---------------------------------------------------------------

def build_dd_graph(
    checkpointer=None
):

    graph = StateGraph(
        DDState
    )

    # Core preparation
    graph.add_node(
        "inventory",
        inventory_node,
    )

    graph.add_node(
        "readiness",
        readiness_node,
    )

    graph.add_node(
        "lead",
        lead_plan_node,
    )

    # Specialist workstreams
    for name, (
        node,
        builder,
    ) in WORKSTREAMS.items():

        graph.add_node(
            node,
            _workstream_node(
                name,
                builder(),
            ),
        )

        graph.add_edge(
            node,
            "merge",
        )

    # Post-analysis
    graph.add_node(
        "merge",
        merge_node,
    )

    graph.add_node(
        "cross_domain",
        cross_domain_guard,
    )

    graph.add_node(
        "verify",
        verify_node,
    )

    # Persistence/review
    graph.add_node(
        "save",
        _scoped(
            save_node
        ),
    )

    graph.add_node(
        "review",
        _scoped(
            review_node
        ),
    )

    graph.add_node(
        "await_evidence",
        _scoped(
            reset_for_reanalysis
        ),
    )

    graph.add_node(
        "finish",
        _scoped(
            finish_node
        ),
    )

    # -----------------------------------------------------------
    # Main flow
    # -----------------------------------------------------------

    graph.add_edge(
        START,
        "inventory",
    )

    graph.add_edge(
        "inventory",
        "readiness",
    )

    graph.add_edge(
        "readiness",
        "lead",
    )

    # Lead dispatches both branches.
    graph.add_conditional_edges(
        "lead",
        fan_out,
    )

    graph.add_edge(
        "merge",
        "cross_domain",
    )

    graph.add_edge(
        "cross_domain",
        "verify",
    )

    graph.add_edge(
        "verify",
        "save",
    )

    graph.add_edge(
        "save",
        "review",
    )

    graph.add_conditional_edges(
        "review",
        _scoped(
            route_after_review
        ),
        {
            "review": "review",
            "await_evidence": "await_evidence",
            "finish": "finish",
        },
    )

    graph.add_edge(
        "await_evidence",
        "inventory",
    )

    graph.add_edge(
        "finish",
        END,
    )

    return graph.compile(
        checkpointer=checkpointer
    )