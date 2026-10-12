from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient

from app.new_main import app
from database.session import SessionLocal
from retrieval.repositories.project_repository import ProjectRepository
from services.project_service import ProjectService
from services.scope_service import ScopeService
from services.task_service import TaskService


@pytest.fixture
def client():
    return TestClient(app)


class TestProjectSetupAndScope:

    def test_create_and_reload_project(self, client):
        """Test creating a project with full details and reloading it."""
        unique_id = uuid.uuid4().hex[:6]
        payload = {
            "name": f"Acquisition of Apex {unique_id}",
            "target_company": f"Apex Systems {unique_id}",
            "deal_type": "Acquisition",
            "industry": "Fintech & SaaS",
            "diligence_period": "Q1 2026",
            "description": "Comprehensive diligence on financial records and customer contracts.",
            "enabled_workstreams": ["financial", "legal"],
        }

        response = client.post("/api/v1/projects", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        project = data["project"]
        project_id = project["id"]
        assert project["name"] == payload["name"]
        assert project["target_company"] == payload["target_company"]
        assert project["deal_type"] == "Acquisition"
        assert project["status"] == "setup"

        workstreams = data["workstreams"]
        assert len(workstreams) == 2
        ws_names = {w["name"] for w in workstreams}
        assert ws_names == {"financial", "legal"}
        assert all(w["enabled"] for w in workstreams)

        # Reload project
        get_res = client.get(f"/api/v1/projects/{project_id}")
        assert get_res.status_code == 200
        reloaded = get_res.json()
        assert reloaded["project"]["name"] == payload["name"]
        assert reloaded["project"]["target_company"] == payload["target_company"]

    def test_update_project_details(self, client):
        """Test updating project details and deal type."""
        proj_service = ProjectService()
        created = proj_service.create_project(
            name="Initial Name",
            target_company="Initial Target",
            deal_type="Series B",
        )
        proj_id = created["project"]["id"]

        update_payload = {
            "name": "Updated Apex Deal",
            "target_company": "Apex Corp Global",
            "deal_type": "Majority Acquisition",
            "status": "in_progress",
        }
        res = client.put(f"/api/v1/projects/{proj_id}", json=update_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["project"]["name"] == "Updated Apex Deal"
        assert data["project"]["target_company"] == "Apex Corp Global"
        assert data["project"]["deal_type"] == "Majority Acquisition"
        assert data["project"]["status"] == "in_progress"

    def test_update_workstreams_enablement(self, client):
        """Test toggling workstreams (e.g., disabling legal, keeping financial)."""
        proj_service = ProjectService()
        created = proj_service.create_project(
            name="Workstream Toggle Test",
            target_company="Target Inc",
        )
        proj_id = created["project"]["id"]

        payload = {
            "workstreams": [
                {"name": "financial", "enabled": True},
                {"name": "legal", "enabled": False},
            ]
        }
        res = client.put(f"/api/v1/projects/{proj_id}/workstreams", json=payload)
        assert res.status_code == 200
        workstreams = res.json()["workstreams"]
        fin = next(w for w in workstreams if w["name"] == "financial")
        leg = next(w for w in workstreams if w["name"] == "legal")
        assert fin["enabled"] is True
        assert leg["enabled"] is False

    def test_save_and_reload_scope_with_custom_questions(self, client):
        """Test saving and retrieving investigation scope with custom questions."""
        proj_service = ProjectService()
        created = proj_service.create_project(
            name="Scope Test Project",
            target_company="Target LLC",
        )
        proj_id = created["project"]["id"]

        custom_scope = {
            "revenue": True,
            "ebitda": True,
            "debt": True,
            "key_questions": [
                "What is the recurring revenue proportion?",
                "Are there off-balance sheet liabilities?",
            ],
            "requested_review_areas": [
                "Top 10 customer contracts",
                "Working capital adjustments",
            ],
        }

        save_res = client.put(
            f"/api/v1/projects/{proj_id}/scope",
            json={"workstream": "financial", "scope": custom_scope},
        )
        assert save_res.status_code == 200
        assert save_res.json()["success"] is True

        # Retrieve specific scope
        get_res = client.get(f"/api/v1/projects/{proj_id}/scope/financial")
        assert get_res.status_code == 200
        retrieved = get_res.json()["scope"]["scope"]
        assert retrieved["revenue"] is True
        assert "recurring revenue proportion" in retrieved["key_questions"][0]

        # Retrieve all scopes endpoint
        all_res = client.get(f"/api/v1/projects/{proj_id}/scopes")
        assert all_res.status_code == 200
        all_scopes = all_res.json()["scopes"]
        assert "financial" in all_scopes
        assert "legal" in all_scopes

    def test_generate_and_track_investigation_tasks(self, client):
        """Test generating real DDTasks for project and tracking their status."""
        proj_service = ProjectService()
        created = proj_service.create_project(
            name="Task Generation Test",
            target_company="Target Tech",
            enabled_workstreams=["financial", "legal"],
        )
        proj_id = created["project"]["id"]

        # Generate plan tasks
        gen_res = client.post(
            f"/api/v1/tasks/project/{proj_id}/generate-plan",
            json={"enabled_workstreams": ["financial", "legal"]},
        )
        assert gen_res.status_code == 200
        tasks = gen_res.json()["tasks"]
        assert len(tasks) >= 4  # 2 financial, 2 legal, 1 cross-domain

        # List project tasks
        list_res = client.get(f"/api/v1/tasks/project/{proj_id}")
        assert list_res.status_code == 200
        db_tasks = list_res.json()
        assert len(db_tasks) >= 4
        assert all(t["status"] == "TODO" for t in db_tasks)

        # Update a task status
        first_task = db_tasks[0]
        patch_res = client.patch(
            f"/api/v1/tasks/{first_task['id']}/status",
            json={"status": "IN_PROGRESS"},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "IN_PROGRESS"

        # Check project summary API
        summary_res = client.get(f"/api/v1/projects/{proj_id}/summary")
        assert summary_res.status_code == 200
        summary = summary_res.json()
        assert summary["project"]["name"] == "Task Generation Test"
        assert summary["counts"]["tasks"] >= 4

    def test_api_validation_and_not_found_handling(self, client):
        """Test handling of invalid inputs and non-existent IDs."""
        # Non-existent project
        res = client.get("/api/v1/projects/NON-EXISTENT-ID-12345")
        assert res.status_code == 404

        # Non-existent task
        task_res = client.get("/api/v1/tasks/NON-EXISTENT-TASK-123")
        assert task_res.status_code == 404

        # Invalid task status update
        dummy_task_id = str(uuid.uuid4())
        invalid_patch = client.patch(
            f"/api/v1/tasks/{dummy_task_id}/status",
            json={"status": "INVALID_STATUS"},
        )
        assert invalid_patch.status_code == 400
