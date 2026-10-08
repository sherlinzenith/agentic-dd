from __future__ import annotations

import json
from typing import Any

from .llm import QwenClient
from .state import AgentState
from .tool_registry import ToolRegistry


class BaseAgent:
    """
    Generic tool-using AI agent.

    Qwen3 is responsible for deciding what to investigate next.
    Python is responsible for safely executing the selected tools.
    """

    def __init__(
        self,
        name: str,
        system_prompt: str,
        tools: ToolRegistry,
        llm: QwenClient | None = None,
    ) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools
        self.llm = llm or QwenClient()

    def build_messages(
        self,
        state: AgentState,
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": self.system_prompt,
            }
        ]

        messages.extend(
            state.get("messages", [])
        )

        if not messages or messages[-1].get("role") != "user":
            messages.append(
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "project_id": state.get(
                                "project_id"
                            ),
                            "investigation_id": state.get(
                                "investigation_id"
                            ),
                            "workstream": state.get(
                                "workstream"
                            ),
                            "objective": state.get(
                                "objective"
                            ),
                            "evidence": state.get(
                                "evidence",
                                [],
                            ),
                            "findings": state.get(
                                "findings",
                                [],
                            ),
                            "missing_information": state.get(
                                "missing_information",
                                [],
                            ),
                            "unresolved_questions": state.get(
                                "unresolved_questions",
                                [],
                            ),
                        },
                        indent=2,
                        default=str,
                    ),
                }
            )

        return messages

    def invoke_llm(
        self,
        state: AgentState,
    ) -> Any:
        return self.llm.chat(
            messages=self.build_messages(state),
            tools=self.tools.schemas(),
        )

    def process_response(
        self,
        state: AgentState,
        response: Any,
    ) -> AgentState:

        message = response.choices[0].message

        state.setdefault(
            "messages",
            [],
        )

        tool_calls = (
            getattr(
                message,
                "tool_calls",
                None,
            )
            or []
        )

        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": message.content or "",
        }

        if tool_calls:
            assistant_message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in tool_calls
            ]

        state["messages"].append(
            assistant_message
        )

        # ---------------------------------------------------------
        # Qwen3 selected one or more tools.
        # Execute them and feed the results back to Qwen3.
        # ---------------------------------------------------------

        if tool_calls:

            for call in tool_calls:

                try:
                    arguments = json.loads(
                        call.function.arguments
                    )
                except json.JSONDecodeError as exc:

                    result = {
                        "status": "ERROR",
                        "message": (
                            "Tool arguments were not valid JSON."
                        ),
                        "error": str(exc),
                    }

                    state.setdefault(
                        "tool_results",
                        [],
                    ).append(
                        {
                            "tool_call_id": call.id,
                            "name": call.function.name,
                            "result": result,
                        }
                    )

                    state["messages"].append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": json.dumps(
                                result
                            ),
                        }
                    )

                    continue

                state.setdefault(
                    "tool_calls",
                    [],
                ).append(
                    {
                        "id": call.id,
                        "name": call.function.name,
                        "arguments": arguments,
                    }
                )

                # Python executes ONLY the tool selected by Qwen3.
                try:
                    result = self.tools.execute(
                        call.function.name,
                        arguments,
                    )

                except Exception as exc:

                    result = {
                        "status": "ERROR",
                        "tool": call.function.name,
                        "message": str(exc),
                    }

                state.setdefault(
                    "tool_results",
                    [],
                ).append(
                    {
                        "tool_call_id": call.id,
                        "name": call.function.name,
                        "result": result,
                    }
                )

                state["messages"].append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(
                            result,
                            default=str,
                        ),
                    }
                )

            # The tool result goes back to Qwen3.
            state["next_action"] = "continue"

            return state

        # ---------------------------------------------------------
        # No tool call = Qwen3 decided the investigation can finish.
        # ---------------------------------------------------------

        state["final_answer"] = (
            message.content or ""
        )

        state["next_action"] = "finish"

        return state
