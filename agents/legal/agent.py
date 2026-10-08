from __future__ import annotations

from agents.engine.base_agent import BaseAgent
from agents.engine.runner import AgentRunner
from agents.engine.tool_registry import ToolRegistry
from agents.engine.tool_registry import AgentTool

from .prompts import LEGAL_AGENT_SYSTEM_PROMPT
from .tools import LegalAgentTools


class LegalAgent(BaseAgent):
    """
    Autonomous Legal Due Diligence Agent.

    Qwen3 decides what to investigate and which tools to use.
    Python executes the selected tools.
    LangGraph manages the investigation loop.
    """

    def __init__(self, max_iterations: int = 12):
        self.legal_tools = LegalAgentTools()

        registry = ToolRegistry()

        registry.register(
            AgentTool(
                name="search_legal_documents",
                description="Search legally classified documents in the project using semantic retrieval.",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "project_id": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["query", "project_id"],
                },
                function=self.legal_tools.search_legal_documents,
            )
        )

        registry.register(
            AgentTool(
                name="search_contract_clause",
                description="Search legal documents for contractual clauses such as change of control, termination, assignment, consent, indemnification, and liability.",
                parameters={
                    "type": "object",
                    "properties": {
                        "clause_query": {"type": "string"},
                        "project_id": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["clause_query", "project_id"],
                },
                function=self.legal_tools.search_contract_clause,
            )
        )

        registry.register(
            AgentTool(
                name="search_legal_evidence",
                description="Search for supporting evidence across legal documents.",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "project_id": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["query", "project_id"],
                },
                function=self.legal_tools.search_legal_evidence,
            )
        )

        registry.register(
            AgentTool(
                name="read_document_page",
                description="Read the contents of a specific document page.",
                parameters={
                    "type": "object",
                    "properties": {
                        "document_id": {"type": "string"},
                        "page_number": {"type": "integer"},
                    },
                    "required": ["document_id", "page_number"],
                },
                function=self.legal_tools.read_document_page,
            )
        )

        registry.register(
            AgentTool(
                name="record_finding",
                description="Record a legal finding supported by evidence.",
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
                function=self.legal_tools.record_finding,
            )
        )

        registry.register(
            AgentTool(
                name="request_evidence",
                description="Request missing legal evidence or documents.",
                parameters={
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "project_id": {"type": "string"},
                    },
                    "required": ["description", "project_id"],
                },
                function=self.legal_tools.request_evidence,
            )
        )

        super().__init__(
            name="legal_agent",
            system_prompt=LEGAL_AGENT_SYSTEM_PROMPT,
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
        """
        Run an autonomous legal DD investigation.
        """

        return self.runner.run(
            project_id=project_id,
            investigation_id=investigation_id,
            workstream="legal",
            objective=objective,
        )
