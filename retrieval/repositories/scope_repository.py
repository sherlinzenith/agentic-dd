from __future__ import annotations

from retrieval.models.scopes import DDScope


class ScopeRepository:

    def __init__(self, session):
        self.session = session

    def create_scope(
        self,
        *,
        project_id: str,
        workstream: str,
        scope: dict,
    ) -> DDScope:

        item = DDScope(
            project_id=project_id,
            workstream=workstream,
            scope=scope,
        )

        self.session.add(item)
        self.session.flush()

        return item

    def get_scope(
        self,
        *,
        project_id: str,
        workstream: str,
    ) -> DDScope | None:

        return (
            self.session.query(DDScope)
            .filter(
                DDScope.project_id == project_id,
                DDScope.workstream == workstream,
            )
            .first()
        )

    def save(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()