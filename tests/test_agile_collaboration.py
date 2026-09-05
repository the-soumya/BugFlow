import urllib.request
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def get_token(email="admin@bugflow.com", password="password123"):
    req = urllib.request.Request(
        f"{BASE_URL}/api/auth/login",
        data=json.dumps({"email": email, "password": password}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read())
        return data["data"]["token"]

def test_agile_collaboration():
    token = get_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    print("=== RUNNING AGILE WORKFLOW & COLLABORATION TEST SUITE ===")

    # -------------------------------------------------------------
    # Test 1 (Priority Math):
    # Submit a CRITICAL severity bug under Security Vulnerability category
    # -> Verify Priority of URGENT (Score: 12.0)
    # -------------------------------------------------------------
    print("\n--- Test 1 (Priority Math) ---")
    triage_payload = {
        "title": "SQL Injection in User Profile Parameter",
        "description": "Vulnerability allows unauthenticated parameter injection",
        "severity": "CRITICAL",
        "category": "Security Vulnerability"
    }
    req1 = urllib.request.Request(
        f"{BASE_URL}/api/v1/issues/triage-recommendation",
        data=json.dumps(triage_payload).encode("utf-8"),
        headers=headers
    )
    with urllib.request.urlopen(req1) as res:
        body = json.loads(res.read())
        assert body["success"] is True
        triage_data = body["data"]
        score = triage_data["priority_score"]
        priority = triage_data["recommended_priority"]
        print(f"Priority Math Result: Score={score}, Priority={priority}, Formula={triage_data['formula']}")
        assert score == 12.0, f"Expected 12.0, got {score}"
        assert priority == "URGENT", f"Expected URGENT, got {priority}"
    print("Test 1 Passed: Score is 12.0 and Priority is URGENT!")

    # -------------------------------------------------------------
    # Test 2 (Smart Match):
    # Submit a bug with the word 'database connection timeout'
    # -> Verify that the backend/database developer appears as top recommendation
    # -------------------------------------------------------------
    print("\n--- Test 2 (Smart Developer Matcher) ---")
    match_payload = {
        "title": "database connection timeout in connection pool under high load",
        "description": "PostgreSQL query hangs and pool exhausts all active sessions",
        "severity": "HIGH",
        "category": "Database"
    }
    req2 = urllib.request.Request(
        f"{BASE_URL}/api/v1/issues/triage-recommendation",
        data=json.dumps(match_payload).encode("utf-8"),
        headers=headers
    )
    with urllib.request.urlopen(req2) as res:
        body = json.loads(res.read())
        devs = body["data"]["recommended_developers"]
        assert len(devs) > 0
        top_dev = devs[0]
        print(f"Top Recommended Dev: {top_dev['name']} ({top_dev['skills']}) - {top_dev['match_percentage']}% match")
        print(f"Rationale: {top_dev['rationale']}")
        assert any(term in top_dev["skills"].lower() for term in ["database", "postgresql", "backend", "python"]), \
            f"Expected database/backend developer, got {top_dev['skills']}"
    print("Test 2 Passed: Backend/Database developer recommended as top match!")

    # -------------------------------------------------------------
    # Test 3 (Chat & Comments):
    # Open a bug, type a comment, refresh page
    # -> Verify comment is still there and visible
    # -------------------------------------------------------------
    print("\n--- Test 3 (Chat & Comments) ---")
    comment_payload = {
        "content": "Automated verification comment: tested on Chrome v120 with valid payload."
    }
    req3_post = urllib.request.Request(
        f"{BASE_URL}/api/v1/collaboration/issues/2/comments",
        data=json.dumps(comment_payload).encode("utf-8"),
        headers=headers
    )
    with urllib.request.urlopen(req3_post) as res:
        created_comment = json.loads(res.read())["data"]
        print(f"Posted comment ID: {created_comment['id']}")
        assert created_comment["content"] == comment_payload["content"]

    req3_get = urllib.request.Request(
        f"{BASE_URL}/api/v1/collaboration/issues/2/comments",
        headers=headers
    )
    with urllib.request.urlopen(req3_get) as res:
        comments = json.loads(res.read())["data"]
        matched = [c for c in comments if c["content"] == comment_payload["content"]]
        assert len(matched) > 0, "Comment was not persisted"
        print(f"Retrieved {len(comments)} comments. Found newly posted comment!")
    print("Test 3 Passed: Comment successfully posted and persisted!")

    # -------------------------------------------------------------
    # Test 4 (Sprint Assignment):
    # Create a new Sprint called 'Sprint 2', click + Add to Sprint on a backlog bug
    # -> Verify the bug moves into Sprint 2
    # -------------------------------------------------------------
    print("\n--- Test 4 (Sprint Assignment) ---")
    sprint_payload = {
        "name": "Sprint 2 - Workflow & Automation",
        "goal": "Agile workflow automation and team collaboration"
    }
    req4_create = urllib.request.Request(
        f"{BASE_URL}/api/v1/sprints/",
        data=json.dumps(sprint_payload).encode("utf-8"),
        headers=headers
    )
    with urllib.request.urlopen(req4_create) as res:
        sprint2 = json.loads(res.read())["data"]
        sprint2_id = sprint2["id"]
        print(f"Created Sprint 2 with ID: {sprint2_id}")

    # Create a fresh issue to guarantee backlog has an issue to assign
    req_create_issue = urllib.request.Request(
        f"{BASE_URL}/api/projects/1/issues",
        data=json.dumps({
            "title": f"Test Backlog Issue {time.time()}",
            "description": "Auto created for sprint assignment test",
            "issue_type": "BUG",
            "priority": "HIGH",
            "severity": "HIGH",
            "category": "Backend Architecture & API"
        }).encode("utf-8"),
        headers=headers
    )
    with urllib.request.urlopen(req_create_issue) as res:
        pass

    # Fetch backlog issues
    req4_backlog = urllib.request.Request(
        f"{BASE_URL}/api/v1/sprints/backlog",
        headers=headers
    )
    with urllib.request.urlopen(req4_backlog) as res:
        backlog = json.loads(res.read())["data"]
        assert len(backlog) > 0, "Expected issues in backlog"
        target_issue = backlog[0]
        target_issue_id = target_issue["id"]
        print(f"Selected backlog issue: {target_issue['issue_key']} (ID: {target_issue_id})")

    # Add issue to Sprint 2
    req4_add = urllib.request.Request(
        f"{BASE_URL}/api/v1/sprints/{sprint2_id}/add-issue/{target_issue_id}",
        data=b"",
        headers=headers
    )
    with urllib.request.urlopen(req4_add) as res:
        updated_issue = json.loads(res.read())["data"]
        assert updated_issue["sprint_id"] == sprint2_id
        print(f"Issue {updated_issue['issue_key']} sprint_id is now {updated_issue['sprint_id']}")
    print("Test 4 Passed: Bug successfully assigned and moved into Sprint 2!")

    # -------------------------------------------------------------
    # Test 5 (Audit Log):
    # Change a bug status -> Verify an entry appears in activity history showing old and new status
    # -------------------------------------------------------------
    print("\n--- Test 5 (Audit Log on Status Change) ---")
    status_payload = {"status": "TRIAGED"}
    req5_status = urllib.request.Request(
        f"{BASE_URL}/api/issues/1/status",
        data=json.dumps(status_payload).encode("utf-8"),
        headers=headers,
        method="PUT"
    )
    with urllib.request.urlopen(req5_status) as res:
        updated = json.loads(res.read())["data"]
        print(f"Updated BUG-1 status to: {updated['status']}")

    # Verify audit log
    req5_audit = urllib.request.Request(
        f"{BASE_URL}/api/issues/1/audit",
        headers=headers
    )
    with urllib.request.urlopen(req5_audit) as res:
        logs = json.loads(res.read())["data"]
        status_logs = [l for l in logs if l["action"] == "STATUS_CHANGED"]
        assert len(status_logs) > 0, "No status change audit log found"
        latest = status_logs[0]
        by_user = latest.get('performed_by', {}).get('name') if latest.get('performed_by') else latest.get('performed_by_id')
        print(f"Audit log found: Action={latest['action']}, Old={latest['old_value']}, New={latest['new_value']}, By={by_user}")
        assert latest["new_value"] == "TRIAGED"

    # -------------------------------------------------------------
    # Test 6 (Activity Stream):
    # Retrieve global activity stream
    # -------------------------------------------------------------
    print("\n--- Test 6 (Live Activity Stream) ---")
    req6 = urllib.request.Request(
        f"{BASE_URL}/api/v1/collaboration/activity-stream",
        headers=headers
    )
    with urllib.request.urlopen(req6) as res:
        feed = json.loads(res.read())["data"]
        assert len(feed) > 0, "Expected items in activity stream"
        latest_act = feed[0]
        print(f"Latest activity: Action={latest_act['action']}, Issue={latest_act.get('issue', {}).get('issue_key')}, PerformedBy={latest_act.get('performed_by', {}).get('name')}")
    print("Test 6 Passed: Global activity stream endpoint works successfully!")

    # -------------------------------------------------------------
    # Test 7 (File Attachment):
    # Upload sample log file
    # -------------------------------------------------------------
    print("\n--- Test 7 (File Attachment Upload) ---")
    boundary = "----BugFlowBoundary987654321"
    body_data = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="crash_dump.log"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
        f"FATAL: Database connection timeout at pool worker 3\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    req7 = urllib.request.Request(
        f"{BASE_URL}/api/v1/collaboration/issues/1/attachments",
        data=body_data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        }
    )
    with urllib.request.urlopen(req7) as res:
        att = json.loads(res.read())["data"]
        print(f"Uploaded attachment: ID={att['id']}, Filename={att['filename']}, Size={att['file_size']} bytes")
        assert att["filename"] == "crash_dump.log"
    print("Test 7 Passed: File attachment uploaded and verified!")

    print("\n==============================================")
    print("ALL 7 AGILE WORKFLOW & COLLABORATION TESTS PASSED SUCCESSFULLY!")
    print("==============================================")

if __name__ == "__main__":
    test_agile_collaboration()
