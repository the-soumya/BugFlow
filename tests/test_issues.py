import pytest
from app.models.issue import Issue, WorkflowState, IssuePriority, IssueSeverity, IssueType
from app.services.triage import calculate_priority_score

def test_priority_score_calculation():
    # Critical (4) * Security (3) = 12.0 -> URGENT
    res1 = calculate_priority_score("CRITICAL", "Security")
    assert res1["priority_score"] == 12.0
    assert res1["recommended_priority"] == "URGENT"

    # High (3) * Database (3) = 9.0 -> HIGH
    res2 = calculate_priority_score("HIGH", "Database")
    assert res2["priority_score"] == 9.0
    assert res2["recommended_priority"] == "HIGH"

    # Low (1) * UI (1) = 1.0 -> LOW
    res3 = calculate_priority_score("LOW", "UI Colors")
    assert res3["priority_score"] == 1.0
    assert res3["recommended_priority"] == "LOW"

def test_issue_creation_and_lifecycle(client, admin_headers, dev_headers):
    # 1. Create a project first or get existing
    proj_res = client.get("/api/projects", headers=admin_headers)
    assert proj_res.status_code == 200
    projects = proj_res.json()["data"]
    assert len(projects) > 0
    project_id = projects[0]["id"]

    # 2. Create an Issue
    issue_payload = {
        "title": "Payment gateway timeout on checkout",
        "description": "When customer clicks pay, gateway times out after 30s.",
        "issue_type": "BUG",
        "priority": "HIGH",
        "severity": "CRITICAL",
        "category": "Backend",
        "sprint_id": None
    }
    create_res = client.post(f"/api/projects/{project_id}/issues", json=issue_payload, headers=admin_headers)
    assert create_res.status_code in [200, 201]
    issue = create_res.json()["data"]
    issue_id = issue["id"]
    assert issue["status"] == "REPORTED"
    assert issue["issue_key"].startswith("BUG-")

    # Assign to developer so developer has permission to update status
    users_res = client.get("/api/auth/users", headers=admin_headers)
    dev_user = next(u for u in users_res.json()["data"] if u["role"] == "DEVELOPER")
    client.put(f"/api/issues/{issue_id}/assign", json={"assignee_id": dev_user["id"]}, headers=admin_headers)

    # 3. Valid State Machine Transition: REPORTED -> TRIAGED
    triaged_res = client.patch(
        f"/api/issues/{issue_id}/status",
        json={"status": "TRIAGED"},
        headers=admin_headers
    )
    assert triaged_res.status_code == 200
    assert triaged_res.json()["data"]["status"] == "TRIAGED"

    # 4. Valid State Machine Transition: TRIAGED -> IN_PROGRESS
    prog_res = client.patch(
        f"/api/issues/{issue_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=dev_headers
    )
    assert prog_res.status_code == 200
    assert prog_res.json()["data"]["status"] == "IN_PROGRESS"

    # 5. Valid State Machine Transition: IN_PROGRESS -> RESOLVED
    res_res = client.patch(
        f"/api/issues/{issue_id}/status",
        json={"status": "RESOLVED"},
        headers=dev_headers
    )
    assert res_res.status_code == 200
    assert res_res.json()["data"]["status"] == "RESOLVED"

    # 6. Verify resolution time is calculated
    get_res = client.get(f"/api/v1/issues/{issue_id}", headers=dev_headers)
    assert get_res.status_code == 200
    resolved_issue = get_res.json()["data"]
    assert resolved_issue["status"] == "RESOLVED"

def test_invalid_state_transition_blocked(client, dev_headers, admin_headers):
    # Create an issue
    proj_res = client.get("/api/projects", headers=admin_headers)
    project_id = proj_res.json()["data"][0]["id"]

    create_res = client.post(f"/api/projects/{project_id}/issues", json={
        "title": "Button color is slightly off",
        "description": "Hex color mismatch in CSS",
        "issue_type": "BUG",
        "priority": "LOW",
        "severity": "LOW",
        "category": "UI"
    }, headers=admin_headers)
    issue_id = create_res.json()["data"]["id"]

    # Assign to developer so developer can modify issue
    users_res = client.get("/api/auth/users", headers=admin_headers)
    dev_user = next(u for u in users_res.json()["data"] if u["role"] == "DEVELOPER")
    client.put(f"/api/issues/{issue_id}/assign", json={"assignee_id": dev_user["id"]}, headers=admin_headers)

    # Developer attempting illegal jump: REPORTED -> RESOLVED directly without triaging/progress
    bad_trans = client.patch(
        f"/api/issues/{issue_id}/status",
        json={"status": "RESOLVED"},
        headers=dev_headers
    )
    assert bad_trans.status_code == 400
    assert "Cannot transition status" in bad_trans.json()["message"]

def test_pagination_and_search_endpoints(client, admin_headers):
    # Test skip and limit pagination
    res = client.get("/api/v1/issues?skip=0&limit=5", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "content" in data
    assert "totalElements" in data
    assert len(data["content"]) <= 5
    assert data["limit"] == 5

