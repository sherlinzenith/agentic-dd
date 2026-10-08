from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from .base_agent import BaseAgent
from .state import AgentState


class AgentRunner:
    """
    Generic LangGraph execution loop for an autonomous agent.

    LangGraph provides stateful execution.
    Qwen3 decides the investigation actions.
    """

    def __init__(
        self,
        agent: BaseAgent,
        max_iterations: int = 12,
    ) -> None:
        self.agent = agent
        self.max_iterations = max_iterations

    def _agent_step(
        self,
        state: AgentState,
    ) -> AgentState:

        iteration = state.get("iteration", 0) + 1
        state["iteration"] = iteration

        if iteration > self.max_iterations:
            state["status"] = "MAX_ITERATIONS"
            state["next_action"] = "finish"
            state["final_answer"] = (
                "The investigation stopped because "
                "the maximum agent iteration limit "
                "was reached."
            )
            return state

        response = self.agent.invoke_llm(state)

        return self.agent.process_response(
            state,
            response,
        )

    @staticmethod
    def _route(
        state: AgentState,
    ) -> str:

        if state.get("next_action") == "continue":
            return "continue"

        return "finish"

    def build_graph(self) -> Any:

        graph = StateGraph(AgentState)

        graph.add_node(
            "agent",
            self._agent_step,
        )

        graph.set_entry_point("agent")

        graph.add_conditional_edges(
            "agent",
            self._route,
            {
                "continue": "agent",
                "finish": END,
            },
        )

        return graph.compile()

    def run(
        self,
        *,
        project_id: str,
        investigation_id: str,
        workstream: str,
        objective: str,
    ) -> AgentState:

        initial_state: AgentState = {
            "project_id": project_id,
            "investigation_id": investigation_id,
            "workstream": workstream,
            "objective": objective,

            "messages": [],

            "tool_calls": [],
            "tool_results": [],

            "evidence": [],
            "findings": [],

            "missing_information": [],
            "unresolved_questions": [],

            "next_action": "continue",
            "status": "RUNNING",

            "iteration": 0,
            "max_iterations": self.max_iterations,

            "final_answer": "",
        }

        graph = self.build_graph()

        result = graph.invoke(initial_state)

        if result.get("status") != "MAX_ITERATIONS":
            if result.get("next_action") == "finish":
                result["status"] = "COMPLETE"

        return result
