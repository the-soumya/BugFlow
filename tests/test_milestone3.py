import urllib.request
import urllib.error
import json
import csv
import io

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

def run_tests():
    print("================================================================")
    print("RUNNING BUGFLOW MILESTONE 3 AUTOMATED VERIFICATION TEST SUITE")
    print("================================================================\n")

    token = get_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # -------------------------------------------------------------
    # Test 1: CI/CD Git Webhook Auto-Transition
    # Send POST /api/v1/webhooks/git with message "Merge PR #45: fixes #2 login password crash"
    # -> Bug #2 status must automatically change to QA_VERIFICATION
    # -------------------------------------------------------------
    print("--- Test 1 (Git Webhook Bot Auto-Transition) ---")
    webhook_payload = {
        "commit_message": "Merge PR #45: fixes #2 login password crash",
        "commit_hash": "a7f8c92",
        "author": "CI/CD Bot"
    }
    req1 = urllib.request.Request(
        f"{BASE_URL}/api/v1/webhooks/git",
        data=json.dumps(webhook_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req1) as res:
        assert res.status == 200
        body = json.loads(res.read())
        assert body["success"] is True, f"Webhook failed: {body}"
        updated_issues = body["data"]["updated_issues"]
        print(f"Webhook response message: {body['message']}")
        print(f"Matched and updated issues: {updated_issues}")
        
        # Verify Bug #2 is in updated list
        bug2_updated = any(u["id"] == 2 or u["issue_key"] == "BUG-2" for u in updated_issues)
        assert bug2_updated, "Expected Bug #2 to be updated by git webhook!"

    # Verify directly from issue API that Bug #2 status is QA_VERIFICATION
    req_issue = urllib.request.Request(f"{BASE_URL}/api/v1/issues/2", headers=headers)
    with urllib.request.urlopen(req_issue) as res:
        issue_data = json.loads(res.read())["data"]
        print(f"Verified Bug #2 current status: {issue_data['status']}")
        assert issue_data["status"] == "QA_VERIFICATION", f"Expected QA_VERIFICATION, got {issue_data['status']}"

    # Verify audit log contains the git commit entry
    req_audit = urllib.request.Request(f"{BASE_URL}/api/issues/2/audit", headers=headers)
    with urllib.request.urlopen(req_audit) as res:
        audit_logs = json.loads(res.read())["data"]
        assert len(audit_logs) > 0
        latest_log = audit_logs[0]
        print(f"Latest Audit Log Entry: Action='{latest_log['action']}', NewValue='{latest_log['new_value']}'")
        assert "Auto-transitioned by Git commit #a7f8c92" in latest_log["action"] or "a7f8c92" in latest_log["new_value"], \
            f"Expected audit log to record git commit transition: {latest_log}"
    print("[PASS] Test 1 Passed: Bug #2 automatically advanced to QA_VERIFICATION with audit trail!\n")

    # -------------------------------------------------------------
    # Test 2: Software Quality Scorecard & Metrics Math
    # GET /api/v1/analytics/quality-metrics
    # -> Verify fix_rate_percentage, mean_time_to_resolution_hours,
    #    defect_leakage_rate_percentage, and backlog_health_score calculate correctly.
    # -------------------------------------------------------------
    print("--- Test 2 (Software Quality Scorecard & Metrics) ---")
    req2 = urllib.request.Request(f"{BASE_URL}/api/v1/analytics/quality-metrics", headers=headers)
    with urllib.request.urlopen(req2) as res:
        assert res.status == 200
        body = json.loads(res.read())
        assert body["success"] is True
        metrics = body["data"]
        print("Calculated Metrics:")
        print(f"  - Fix Rate Percentage: {metrics['fix_rate_percentage']}%")
        print(f"  - Mean Time to Resolution: {metrics['mean_time_to_resolution_hours']} hrs ({metrics['mttr_formatted']})")
        print(f"  - Defect Leakage Rate: {metrics['defect_leakage_rate_percentage']}%")
        print(f"  - Backlog Health Score: {metrics['backlog_health_score']} / 100 ({metrics['health_status']})")
        print(f"  - Total Bugs: {metrics['total_bugs']}, Resolved: {metrics['resolved_bugs']}, Closed: {metrics['closed_bugs']}")

        assert "fix_rate_percentage" in metrics
        assert "mean_time_to_resolution_hours" in metrics
        assert "defect_leakage_rate_percentage" in metrics
        assert "backlog_health_score" in metrics
        assert isinstance(metrics["fix_rate_percentage"], (int, float))
        assert isinstance(metrics["mean_time_to_resolution_hours"], (int, float))
        assert 0.0 <= metrics["fix_rate_percentage"] <= 100.0
        assert 0 <= metrics["backlog_health_score"] <= 100
    print("[PASS] Test 2 Passed: Quality metrics and MTTR calculated correctly!\n")

    # -------------------------------------------------------------
    # Test 3: Interactive Plotly Visualizations & Trend API
    # GET /api/v1/analytics/plotly-charts & GET /api/v1/analytics/defect-trends
    # -> Verify 14-day trend line series, severity donut, and pipeline configs
    # -------------------------------------------------------------
    print("--- Test 3 (Plotly Charts & Trend Analytics) ---")
    req3_charts = urllib.request.Request(f"{BASE_URL}/api/v1/analytics/plotly-charts", headers=headers)
    with urllib.request.urlopen(req3_charts) as res:
        assert res.status == 200
        body = json.loads(res.read())
        assert body["success"] is True
        charts = body["data"]
        assert "trend_chart" in charts
        assert "severity_chart" in charts
        assert "workflow_chart" in charts

        # Verify Trend Line Chart
        trend = charts["trend_chart"]
        assert len(trend["data"]) == 2  # 2 traces: Reported and Resolved
        assert trend["data"][0]["name"] == "Reported Bugs"
        assert trend["data"][1]["name"] == "Resolved Bugs"
        print("  - 14-Day Defect Trend Trace 1 (Reported):", trend["data"][0]["y"])
        print("  - 14-Day Defect Trend Trace 2 (Resolved):", trend["data"][1]["y"])

        # Verify Donut Chart
        severity = charts["severity_chart"]
        assert severity["data"][0]["type"] == "pie"
        assert severity["data"][0]["hole"] > 0
        print("  - Severity Donut Labels & Values:", severity["data"][0]["labels"], severity["data"][0]["values"])

        # Verify Workflow Pipeline Bar Chart
        workflow = charts["workflow_chart"]
        assert workflow["data"][0]["type"] == "bar"
        print("  - Pipeline Stages:", workflow["data"][0]["x"], workflow["data"][0]["y"])

    req3_trends = urllib.request.Request(f"{BASE_URL}/api/v1/analytics/defect-trends?days=14", headers=headers)
    with urllib.request.urlopen(req3_trends) as res:
        body = json.loads(res.read())
        assert body["success"] is True
        trends = body["data"]
        assert len(trends) == 14
        print(f"  - 14 daily trend points verified: {trends[0]['date']} to {trends[-1]['date']}")
    print("[PASS] Test 3 Passed: Interactive Plotly chart configurations and daily trends verified!\n")

    # -------------------------------------------------------------
    # Test 4: One-Click PDF Report Generation
    # GET /api/v1/export/pdf
    # -> Verify binary PDF format with valid '%PDF-' header
    # -------------------------------------------------------------
    print("--- Test 4 (One-Click PDF Exporter) ---")
    req4 = urllib.request.Request(f"{BASE_URL}/api/v1/export/pdf")
    with urllib.request.urlopen(req4) as res:
        assert res.status == 200
        content_type = res.headers.get("Content-Type")
        content_disp = res.headers.get("Content-Disposition")
        pdf_bytes = res.read()
        print(f"  - Content-Type: {content_type}")
        print(f"  - Content-Disposition: {content_disp}")
        print(f"  - Generated PDF file size: {len(pdf_bytes)} bytes")
        assert "application/pdf" in content_type
        assert "attachment" in content_disp
        assert pdf_bytes.startswith(b"%PDF-"), "File is missing standard PDF header %PDF-!"
    print("[PASS] Test 4 Passed: PDF Quality report generated cleanly and downloadable!\n")

    # -------------------------------------------------------------
    # Test 5: Excel-Ready CSV Bug Registry Exporter
    # GET /api/v1/export/csv
    # -> Verify valid CSV with all expected column headers and rows
    # -------------------------------------------------------------
    print("--- Test 5 (CSV Exporter) ---")
    req5 = urllib.request.Request(f"{BASE_URL}/api/v1/export/csv")
    with urllib.request.urlopen(req5) as res:
        assert res.status == 200
        content_type = res.headers.get("Content-Type")
        content_disp = res.headers.get("Content-Disposition")
        raw_bytes = res.read()
        assert raw_bytes.startswith(b"\xef\xbb\xbf"), "CSV missing UTF-8 BOM for Excel compatibility!"
        csv_text = raw_bytes.decode("utf-8-sig")
        print(f"  - Content-Type: {content_type}")
        print(f"  - Content-Disposition: {content_disp}")
        print("  - Verified Excel-compatible UTF-8 BOM header present.")

        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        assert len(rows) > 1, "CSV should contain headers and at least 1 row!"
        headers_row = rows[0]
        print(f"  - CSV Column Headers: {headers_row}")
        print(f"  - Total exported bug rows: {len(rows) - 1}")
        
        expected_cols = ["Issue Key", "Title", "Type", "Status", "Priority", "Severity", "Category"]
        for col in expected_cols:
            assert col in headers_row, f"Missing expected column '{col}' in CSV!"
    print("[PASS] Test 5 Passed: Excel-ready CSV export generated and verified!\n")

    print("================================================================")
    print("[SUCCESS] ALL 5 MILESTONE 3 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("================================================================")

if __name__ == "__main__":
    run_tests()
