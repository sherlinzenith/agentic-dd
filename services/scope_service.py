from __future__ import annotations

from database.session import SessionLocal
from retrieval.repositories.scope_repository import ScopeRepository


class ScopeService:

    DEFAULT_SCOPES = {
        "financial": {
            "revenue": True,
            "revenue_growth": True,
            "gross_profit": True,
            "ebitda": True,
            "operating_expenses": True,
            "cash_flow": True,
            "debt": True,
            "working_capital": True,
            "accounts_receivable": True,
            "inventory": True,
            "related_party_transactions": True,
            "financial_inconsistencies": True,
            "missing_financial_documents": True,
        },
        "legal": {
            "material_contracts": True,
            "contract_expiry": True,
            "change_of_control": True,
            "termination_clauses": True,
            "litigation": True,
            "liabilities": True,
            "ip_ownership": True,
            "employment_obligations": True,
            "regulatory_issues": True,
            "missing_legal_documents": True,
            "unusual_clauses": True,
        },
    }

    def save_scope(
        self,
        *,
        project_id: str,
        workstream: str,
        scope: dict,
    ) -> dict:

        if workstream not in self.DEFAULT_SCOPES:
            raise ValueError(
                f"Unsupported workstream: {workstream}"
            )

        session = SessionLocal()

        try:
            repository = ScopeRepository(session)

            existing = repository.get_scope(
                project_id=project_id,
                workstream=workstream,
            )

            if existing:
                existing.scope = scope
            else:
                existing = repository.create_scope(
                    project_id=project_id,
                    workstream=workstream,
                    scope=scope,
                )

            repository.save()

            return {
                "id": existing.id,
                "project_id": existing.project_id,
                "workstream": existing.workstream,
                "scope": existing.scope,
            }

        except Exception:
            session.rollback()
            raise

        finally:
            session.close()

    def get_scope(
        self,
        *,
        project_id: str,
        workstream: str,
    ) -> dict:

        if workstream not in self.DEFAULT_SCOPES:
            raise ValueError(
                f"Unsupported workstream: {workstream}"
            )

        session = SessionLocal()

        try:
            repository = ScopeRepository(session)

            existing = repository.get_scope(
                project_id=project_id,
                workstream=workstream,
            )

            if existing:
                return {
                    "id": existing.id,
                    "project_id": existing.project_id,
                    "workstream": existing.workstream,
                    "scope": existing.scope,
                }

            return {
                "id": None,
                "project_id": project_id,
                "workstream": workstream,
                "scope": self.DEFAULT_SCOPES[workstream],
            }

        finally:
            session.close()