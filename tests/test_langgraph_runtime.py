from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from agents.engine.runner import AgentRunner
from agents.engine.state import AgentState
from workflow.orchestrator import build_dd_graph


class TestLangGraphRuntime:
    """
    Verification suite for LangGraph graph construction, node execution,
    state propagation, conditional routing, and checkpoint/resume behavior.
    """

    def test_agent_runner_graph_construction_and_execution(self):
        """
        Verify that AgentRunner compiles a real LangGraph StateGraph,
        invokes nodes in order, updates state, and routes correctly to END.
        """
        mock_agent = MagicMock()
        # Mock step 1: tool call / continue
        # Mock step 2: finish
        step1_response = MagicMock()
        mock_msg1 = MagicMock()
        mock_msg1.content = ""
        mock_msg1.tool_calls = []
        step1_response.choices = [MagicMock(message=mock_msg1)]

        def side_effect_process(state, resp):
            if state["iteration"] == 1:
                state["next_action"] = "continue"
                state["tool_calls"].append({"name": "test_tool", "arguments": {}})
            else:
                state["next_action"] = "finish"
                state["final_answer"] = "Analysis concluded successfully."
            return state

        mock_agent.invoke_llm.return_value = step1_response
        mock_agent.process_response.side_effect = side_effect_process

        runner = AgentRunner(agent=mock_agent, max_iterations=5)
        graph = runner.build_graph()

        # Assert compiled LangGraph object
        assert graph is not None
        assert hasattr(graph, "invoke")

        # Invoke the graph with initial state
        result = runner.run(
            project_id="TEST-LG-PROJ",
            investigation_id="TEST-LG-INV",
            workstream="financial",
            objective="Verify LangGraph state loop execution",
        )

        assert result["status"] == "COMPLETE"
        assert result["iteration"] == 2
        assert result["final_answer"] == "Analysis concluded successfully."
        assert len(result["tool_calls"]) == 1
        assert result["next_action"] == "finish"

    def test_agent_runner_max_iterations_conditional_edge(self):
        """
        Verify that exceeding max_iterations triggers the termination branch
        without hanging in an infinite loop.
        """
        mock_agent = MagicMock()
        mock_agent.invoke_llm.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content="", tool_calls=[]))])
        mock_agent.process_response.side_effect = lambda state, resp: {
            **state,
            "next_action": "continue",
        }

        runner = AgentRunner(agent=mock_agent, max_iterations=2)
        result = runner.run(
            project_id="TEST-MAX-PROJ",
            investigation_id="TEST-MAX-INV",
            workstream="legal",
            objective="Test max iterations termination",
        )

        assert result["status"] == "MAX_ITERATIONS"
        assert result["iteration"] == 3
        assert result["next_action"] == "finish"
        assert "maximum agent iteration limit" in result["final_answer"]

    def test_dd_graph_construction_and_checkpointer_inspection(self):
        """
        Verify multi-agent StateGraph construction with checkpointer
        and state inspection.
        """
        checkpointer = MemorySaver()
        graph = build_dd_graph(checkpointer=checkpointer)

        assert graph is not None
        config = {"configurable": {"thread_id": "LG-TEST-JOB-001"}}

        # Verify initial empty state snapshot
        snapshot = graph.get_state(config)
        assert snapshot.values == {}
