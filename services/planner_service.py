from __future__ import annotations

import json
from typing import Any

from database.session import SessionLocal
from retrieval.repositories.investigation_repository import (
    InvestigationRepository,
)

from agents.planner.agent import PlannerRunner


class PlannerService:

    def __init__(self):
        self.runner = PlannerRunner(
            max_iterations=10,
        )

    def start_investigation(
        self,
        *,
        project_id: str,
        objective: str,
    ) -> dict[str, Any]:

        session = SessionLocal()

        try:
            repository = InvestigationRepository(session)

            investigation = repository.create(
                project_id=project_id,
                objective=objective,
            )

            repository.save()

            investigation_id = investigation.id

        except Exception:
            session.rollback()
            raise

        finally:
            session.close()

        # Run the real Planner Agent.
        result = self.runner.run(
            project_id=project_id,
            investigation_id=investigation_id,
            objective=objective,
        )

        plan = self._build_plan_from_result(result)

        session = SessionLocal()

        try:
            repository = InvestigationRepository(session)

            updated = repository.update_plan(
                investigation_id=investigation_id,
                plan=plan,
            )

            if updated is None:
                raise ValueError(
                    "Investigation was not found after planner execution."
                )

            repository.save()

            return {
                "investigation_id": investigation_id,
                "project_id": project_id,
                "status": updated.status,
                "objective": updated.objective,
                "plan": updated.plan,
                "agent_status": result.get("status"),
                "iterations": result.get("iteration", 0),
                "final_answer": result.get("final_answer", ""),
            }

        except Exception:
            session.rollback()
            raise

        finally:
            session.close()

    def get_investigation(
        self,
        investigation_id: str,
    ) -> dict[str, Any] | None:

        session = SessionLocal()

        try:
            repository = InvestigationRepository(session)

            investigation = repository.get(
                investigation_id
            )

            if investigation is None:
                return None

            return {
                "id": investigation.id,
                "project_id": investigation.project_id,
                "status": investigation.status,
                "objective": investigation.objective,
                "plan": investigation.plan,
                "created_at": investigation.created_at,
                "updated_at": investigation.updated_at,
            }

        finally:
            session.close()

    @staticmethod
    def _build_plan_from_result(
        result: dict[str, Any],
    ) -> dict[str, Any]:

        final_answer = result.get(
            "final_answer",
            "",
        )

        # Prefer structured JSON if Qwen returns it.
        if final_answer:

            try:
                parsed = json.loads(
                    final_answer
                )

                if isinstance(parsed, dict):
                    return parsed

            except (json.JSONDecodeError, TypeError):
                pass

        # Preserve the real agent output rather than inventing
        # structured findings when the model returned plain text.
        return {
            "summary": "Planner agent completed its reasoning.",
            "agent_output": final_answer,
            "tasks": [],
            "missing_information": result.get(
                "missing_information",
                [],
            ),
            "unresolved_questions": result.get(
                "unresolved_questions",
                [],
            ),
        }
