from __future__ import annotations

from agents.engine.base_agent import BaseAgent
from agents.engine.tool_registry import AgentTool, ToolRegistry
from agents.financial.prompts import FINANCIAL_AGENT_SYSTEM_PROMPT
from agents.financial.tools import (
    calculate_metric,
    compare_periods,
    extract_financial_table,
    read_document_page,
    record_finding,
    reconcile_values,
    search_evidence,
    search_financial_documents,
)


def create_financial_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(
        AgentTool(
            name="search_financial_documents",
            description=(
                "Search project documents for information relevant "
                "to the financial investigation."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Information to search for.",
                    },
                    "project_id": {
                        "type": "string",
                        "description": "DD project identifier.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results.",
                        "default": 10,
                    },
                },
                "required": [
                    "query",
                    "project_id",
                ],
            },
            function=search_financial_documents,
        )
    )

    registry.register(
        AgentTool(
            name="read_document_page",
            description=(
                "Read a specific page of a source document when "
                "precise evidence is required."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                    },
                    "page": {
                        "type": "integer",
                        "description": "1-based page number.",
                    },
                },
                "required": [
                    "document_id",
                    "page",
                ],
            },
            function=read_document_page,
        )
    )

    registry.register(
        AgentTool(
            name="extract_financial_table",
            description=(
                "Extract a structured financial table or set of "
                "financial values from a source document."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                    },
                    "table_description": {
                        "type": "string",
                    },
                },
                "required": [
                    "document_id",
                    "table_description",
                ],
            },
            function=extract_financial_table,
        )
    )

    registry.register(
        AgentTool(
            name="calculate_metric",
            description=(
                "Perform deterministic arithmetic needed during "
                "financial investigation."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": (
                            "Arithmetic expression using numeric "
                            "values and + - * / %."
                        ),
                    },
                },
                "required": [
                    "expression",
                ],
            },
            function=calculate_metric,
        )
    )

    registry.register(
        AgentTool(
            name="compare_periods",
            description=(
                "Compare a financial metric across two periods."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "metric": {"type": "string"},
                    "period_a": {"type": "string"},
                    "value_a": {"type": "number"},
                    "period_b": {"type": "string"},
                    "value_b": {"type": "number"},
                },
                "required": [
                    "metric",
                    "period_a",
                    "value_a",
                    "period_b",
                    "value_b",
                ],
            },
            function=compare_periods,
        )
    )

    registry.register(
        AgentTool(
            name="reconcile_values",
            description=(
                "Compare values reported by two different sources "
                "and identify discrepancies."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "source_a": {"type": "string"},
                    "value_a": {"type": "number"},
                    "source_b": {"type": "string"},
                    "value_b": {"type": "number"},
                },
                "required": [
                    "item",
                    "source_a",
                    "value_a",
                    "source_b",
                    "value_b",
                ],
            },
            function=reconcile_values,
        )
    )

    registry.register(
        AgentTool(
            name="search_evidence",
            description=(
                "Search the project's available evidence for "
                "supporting information."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "project_id": {"type": "string"},
                    "limit": {
                        "type": "integer",
                        "default": 10,
                    },
                },
                "required": [
                    "query",
                    "project_id",
                ],
            },
            function=search_evidence,
        )
    )

    registry.register(
        AgentTool(
            name="record_finding",
            description=(
                "Record a financially material finding after "
                "sufficient evidence has been collected."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "issue": {"type": "string"},
                    "why_it_matters": {"type": "string"},
                    "conclusion": {"type": "string"},
                    "risk_level": {
                        "type": "string",
                        "enum": [
                            "low",
                            "medium",
                            "high",
                            "critical",
                        ],
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                        },
                    },
                    "recommended_action": {
                        "type": [
                            "string",
                            "null",
                        ],
                    },
                },
                "required": [
                    "title",
                    "issue",
                    "why_it_matters",
                    "conclusion",
                    "risk_level",
                    "confidence",
                    "evidence",
                ],
            },
            function=record_finding,
        )
    )

    return registry


def create_financial_agent() -> BaseAgent:
    return BaseAgent(
        name="financial_dd_agent",
        system_prompt=FINANCIAL_AGENT_SYSTEM_PROMPT,
        tools=create_financial_tool_registry(),
    )
