from __future__ import annotations

import json

from agents.engine.base_agent import BaseAgent
from agents.engine.runner import AgentRunner

from .prompts import PLANNER_SYSTEM_PROMPT
from .tools import create_planner_tool_registry


class PlannerAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name="lead_planner",
            system_prompt=PLANNER_SYSTEM_PROMPT,
            tools=create_planner_tool_registry(),
        )


class PlannerRunner:

    def __init__(
        self,
        max_iterations: int = 10,
    ):
        self.agent = PlannerAgent()
        self.runner = AgentRunner(
            agent=self.agent,
            max_iterations=max_iterations,
        )

    def run(
        self,
        *,
        project_id: str,
        investigation_id: str,
        objective: str,
    ):

        return self.runner.run(
            project_id=project_id,
            investigation_id=investigation_id,
            workstream="planner",
            objective=objective,
        )
