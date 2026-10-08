from __future__ import annotations

from agents.engine.base_agent import BaseAgent
from agents.engine.runner import AgentRunner
from agents.engine.tool_registry import ToolRegistry
from agents.engine.tool_registry import AgentTool

from .prompts import CROSS_DOMAIN_AGENT_SYSTEM_PROMPT
from .tools import CrossDomainAgentTools


class CrossDomainAgent(BaseAgent):
    """
    Autonomous Cross-Domain Due Diligence Agent.

    Qwen3 decides what relationships to investigate.
    Python executes the selected tools.
    LangGraph manages the investigation loop.
    """

    def __init__(self, max_iterations: int = 12):

        self.cross_domain_tools = CrossDomainAgentTools()

        registry = ToolRegistry()

        registry.register(
            AgentTool(
                name="search_cross_domain_evidence",
                description="Search Financial and Legal documents for evidence relevant to a cross-domain investigation.",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "project_id": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["query", "project_id"],
                },
                function=self.cross_domain_tools.search_cross_domain_evidence,
            )
        )

        registry.register(
            AgentTool(
                name="compare_findings",
                description="Compare Financial and Legal findings to identify relationships, contradictions, and dependencies.",
                parameters={
                    "type": "object",
                    "properties": {
                        "financial_findings": {
                            "type": "array",
                            "items": {"type": "object"},
                        },
                        "legal_findings": {
                            "type": "array",
                            "items": {"type": "object"},
                        },
                    },
                    "required": ["financial_findings", "legal_findings"],
                },
                function=self.cross_domain_tools.compare_findings,
            )
        )

        registry.register(
            AgentTool(
                name="inspect_evidence",
                description="Inspect and organize evidence collected from Financial and Legal investigations.",
                parameters={
                    "type": "object",
                    "properties": {
                        "evidence": {
                            "type": "array",
                            "items": {"type": "object"},
                        },
                    },
                    "required": ["evidence"],
                },
                function=self.cross_domain_tools.inspect_evidence,
            )
        )

        registry.register(
            AgentTool(
                name="record_cross_domain_finding",
                description="Record a cross-domain finding supported by evidence.",
                parameters={
                    "type": "object",
                    "properties": {
                        "finding": {
                            "type": "object",
                            "additionalProperties": True,
                        },
                    },
                    "required": ["finding"],
                },
                function=self.cross_domain_tools.record_cross_domain_finding,
            )
        )

        registry.register(
            AgentTool(
                name="request_additional_evidence",
                description="Request additional evidence needed to resolve a cross-domain investigation.",
                parameters={
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "project_id": {"type": "string"},
                    },
                    "required": ["description", "project_id"],
                },
                function=self.cross_domain_tools.request_additional_evidence,
            )
        )

        super().__init__(
            name="cross_domain_agent",
            system_prompt=CROSS_DOMAIN_AGENT_SYSTEM_PROMPT,
            tools=registry,
        )

        self.runner = AgentRunner(
            agent=self,
            max_iterations=max_iterations,
        )

    def investigate(
        self,
        *,
        project_id: str,
        investigation_id: str,
        objective: str,
    ):

        return self.runner.run(
            project_id=project_id,
            investigation_id=investigation_id,
            workstream="cross_domain",
            objective=objective,
        )
