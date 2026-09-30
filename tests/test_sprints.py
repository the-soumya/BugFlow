import pytest
from datetime import datetime, timedelta

def test_sprint_creation_and_backlog_workflow(client, admin_headers):
    # 1. Get Project ID
    proj_res = client.get("/api/projects", headers=admin_headers)
    assert proj_res.status_code == 200
    project_id = proj_res.json()["data"][0]["id"]

    # 2. Create a new Sprint
    now = datetime.utcnow()
    sprint_payload = {
        "project_id": project_id,
        "name": "Sprint 2 - Performance & Load",
        "goal": "Optimize connection pooling and reduce MTTR under load",
        "start_date": (now).isoformat(),
        "end_date": (now + timedelta(days=14)).isoformat(),
        "status": "ACTIVE"
    }
    sprint_res = client.post("/api/v1/sprints/", json=sprint_payload, headers=admin_headers)
    assert sprint_res.status_code in [200, 201]
    sprint_data = sprint_res.json()["data"]
    sprint_id = sprint_data["id"]
    assert sprint_data["name"] == "Sprint 2 - Performance & Load"

    # 3. Create a Backlog Issue
    issue_payload = {
        "title": "Database connection pool timeout during stress testing",
        "description": "Connection pool exhausted during locust simulation",
        "issue_type": "BUG",
        "priority": "HIGH",
        "severity": "HIGH",
        "category": "Database",
        "sprint_id": None
    }
    create_issue_res = client.post(f"/api/projects/{project_id}/issues", json=issue_payload, headers=admin_headers)
    assert create_issue_res.status_code in [200, 201]
    issue_id = create_issue_res.json()["data"]["id"]

    # 4. Check that issue appears in Backlog
    backlog_res = client.get("/api/v1/sprints/backlog", headers=admin_headers)
    assert backlog_res.status_code == 200
    backlog_issues = backlog_res.json()["data"]
    assert any(i["id"] == issue_id for i in backlog_issues)

    # 5. Move Issue from Backlog into the Sprint
    move_res = client.post(f"/api/v1/sprints/{sprint_id}/add-issue/{issue_id}", headers=admin_headers)
    assert move_res.status_code == 200
    assert move_res.json()["data"]["sprint_id"] == sprint_id

    # 6. Resolve issue in sprint
    client.patch(f"/api/issues/{issue_id}/status", json={"status": "TRIAGED"}, headers=admin_headers)
    client.patch(f"/api/issues/{issue_id}/status", json={"status": "IN_PROGRESS"}, headers=admin_headers)
    client.patch(f"/api/issues/{issue_id}/status", json={"status": "RESOLVED"}, headers=admin_headers)

    # 7. Complete the Sprint and verify velocity calculation
    complete_res = client.put(
        f"/api/v1/sprints/{sprint_id}/status",
        json={"status": "COMPLETED"},
        headers=admin_headers
    )
    assert complete_res.status_code == 200
    completed_sprint = complete_res.json()["data"]
    assert completed_sprint["status"] == "COMPLETED"
    assert completed_sprint["velocity"] >= 1
