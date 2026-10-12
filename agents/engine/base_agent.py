from __future__ import annotations

import json
import re
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

        has_user_message = any(
            m.get("role") == "user"
            for m in messages
        )

        if not has_user_message:
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

        assistant_content = message.content or ""

        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": assistant_content,
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

                # Auto-inject project_id and investigation_id from state if tool supports them
                if isinstance(arguments, dict):
                    tool_obj = self.tools._tools.get(call.function.name)
                    if tool_obj:
                        tool_props = tool_obj.parameters.get("properties", {})
                        if "project_id" in tool_props:
                            if not arguments.get("project_id") or arguments.get("project_id") == "REAL-INGESTION-TEST":
                                if state.get("project_id"):
                                    arguments["project_id"] = state["project_id"]
                        if "investigation_id" in tool_props:
                            if not arguments.get("investigation_id"):
                                if state.get("investigation_id"):
                                    arguments["investigation_id"] = state["investigation_id"]

                    # If tool argument has a nested 'finding' dictionary, inject into it as well
                    if "finding" in arguments and isinstance(arguments["finding"], dict):
                        if not arguments["finding"].get("project_id") or arguments["finding"].get("project_id") == "REAL-INGESTION-TEST":
                            if state.get("project_id"):
                                arguments["finding"]["project_id"] = state["project_id"]
                        if not arguments["finding"].get("investigation_id"):
                            if state.get("investigation_id"):
                                arguments["finding"]["investigation_id"] = state["investigation_id"]

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

        content = (message.content or "").strip()
        reasoning = getattr(message, "reasoning", "") or getattr(message, "reasoning_content", "") or ""

        if content:
            state["final_answer"] = content
        else:
            # If the model exhausted tokens or placed a structured result in reasoning,
            # attempt to extract a clean conclusion or JSON block without exposing raw chain-of-thought.
            extracted_conclusion = None
            if reasoning:
                # Check for explicit conclusion or final answer markers
                match = re.search(r"(?:Final Answer|Conclusion|In summary|Summary):\s*(.+?)(?:\n\n|\Z)", reasoning, re.DOTALL | re.IGNORECASE)
                if match:
                    extracted_conclusion = match.group(1).strip()
                elif "{" in reasoning and "}" in reasoning:
                    try:
                        start = reasoning.find("{")
                        end = reasoning.rfind("}")
                        parsed = json.loads(reasoning[start:end+1])
                        if isinstance(parsed, dict) and ("findings" in parsed or "summary" in parsed):
                            extracted_conclusion = json.dumps(parsed, indent=2)
                    except Exception:
                        pass

            if extracted_conclusion:
                state["final_answer"] = extracted_conclusion
            else:
                workstream_label = state.get("workstream", "due diligence").capitalize()
                state["final_answer"] = (
                    f"{workstream_label} agent investigation concluded. "
                    "Review recorded findings, metrics, and validated evidence in the diligence register."
                )

        state["next_action"] = "finish"

        return state
