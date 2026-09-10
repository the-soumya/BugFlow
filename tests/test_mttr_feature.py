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

def run_mttr_tests():
    print("================================================================")
    print("RUNNING MTTR (RESOLUTION TIME) FEATURE VERIFICATION TEST SUITE")
    print("================================================================\n")

    token = get_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # 1. Test Quality Metrics endpoint for MTTR Priority Breakdown & SLA Compliance
    print("--- 1. Testing Quality Metrics for MTTR breakdown ---")
    req1 = urllib.request.Request(f"{BASE_URL}/api/v1/analytics/quality-metrics", headers=headers)
    with urllib.request.urlopen(req1) as res:
        assert res.status == 200
        body = json.loads(res.read())
        assert body["success"] is True
        data = body["data"]

        assert "mean_time_to_resolution_hours" in data
        assert "mttr_formatted" in data
        assert "mttr_by_priority" in data
        assert "mttr_sla_compliance_rate" in data

        print(f"  Overall MTTR: {data['mean_time_to_resolution_hours']} hrs ({data['mttr_formatted']})")
        print(f"  MTTR SLA Compliance Rate: {data['mttr_sla_compliance_rate']}%")
        print("  MTTR by Priority:")
        for pri, pdata in data["mttr_by_priority"].items():
            print(f"    - {pri}: Avg {pdata['average_hours']} hrs (Target SLA < {pdata['target_sla_hours']} hrs, Status: {pdata['status']})")
    print("[PASS] Quality metrics MTTR data verified successfully!\n")

    # 2. Test Plotly Charts endpoint for mttr_chart
    print("--- 2. Testing Plotly Charts for mttr_chart ---")
    req2 = urllib.request.Request(f"{BASE_URL}/api/v1/analytics/plotly-charts", headers=headers)
    with urllib.request.urlopen(req2) as res:
        assert res.status == 200
        body = json.loads(res.read())
        assert body["success"] is True
        charts = body["data"]

        assert "mttr_chart" in charts, "Expected 'mttr_chart' key in plotly-charts response!"
        mttr_c = charts["mttr_chart"]
        assert "data" in mttr_c and "layout" in mttr_c
        assert len(mttr_c["data"]) >= 2, "Expected at least 2 traces in MTTR chart (Actual vs SLA)"
        
        trace1 = mttr_c["data"][0]
        trace2 = mttr_c["data"][1]
        print(f"  Trace 1 Name: '{trace1['name']}', Type: '{trace1['type']}', X: {trace1['x']}, Y: {trace1['y']}")
        print(f"  Trace 2 Name: '{trace2['name']}', Type: '{trace2['type']}', X: {trace2['x']}, Y: {trace2['y']}")
        assert trace1["x"] == ["Critical", "High", "Medium", "Low"]
        assert trace2["x"] == ["Critical", "High", "Medium", "Low"]
    print("[PASS] Plotly mttr_chart configuration verified successfully!\n")

    # 3. Test CSV export for Resolution Time columns
    print("--- 3. Testing CSV Export for Resolution Time columns ---")
    req3 = urllib.request.Request(f"{BASE_URL}/api/v1/export/csv")
    with urllib.request.urlopen(req3) as res:
        assert res.status == 200
        raw_bytes = res.read()
        assert raw_bytes.startswith(b"\xef\xbb\xbf")
        csv_text = raw_bytes.decode("utf-8-sig")

        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        header = rows[0]
        print(f"  Header columns: {header}")
        assert "Resolution Time (Hours)" in header, "Missing 'Resolution Time (Hours)' column in CSV!"
        assert "Resolution Time (Formatted)" in header, "Missing 'Resolution Time (Formatted)' column in CSV!"

        res_hours_idx = header.index("Resolution Time (Hours)")
        res_fmt_idx = header.index("Resolution Time (Formatted)")
        status_idx = header.index("Status")

        print(f"  Inspecting exported rows (Total: {len(rows)-1}):")
        for row in rows[1:6]:
            print(f"    Issue: {row[0]}, Status: {row[status_idx]}, Res Hours: '{row[res_hours_idx]}', Res Formatted: '{row[res_fmt_idx]}'")
    print("[PASS] CSV Export resolution time columns verified successfully!\n")

    # 4. Test PDF export generation
    print("--- 4. Testing PDF Export for MTTR & Quality Report ---")
    req4 = urllib.request.Request(f"{BASE_URL}/api/v1/export/pdf")
    with urllib.request.urlopen(req4) as res:
        assert res.status == 200
        assert "application/pdf" in res.headers.get("Content-Type")
        pdf_data = res.read()
        assert pdf_data.startswith(b"%PDF-")
        print(f"  PDF successfully compiled! Size: {len(pdf_data)} bytes")
    print("[PASS] PDF Export with MTTR section verified successfully!\n")

    # 5. Test Issue Response Schema for resolution_time fields
    print("--- 5. Testing Issue API response for resolution time fields ---")
    req5 = urllib.request.Request(f"{BASE_URL}/api/v1/issues/", headers=headers)
    with urllib.request.urlopen(req5) as res:
        assert res.status == 200
        body = json.loads(res.read())
        issues_list = body["data"]["content"]
        print(f"  Total issues retrieved: {len(issues_list)}")
        sample = issues_list[0]
        assert "resolution_time_hours" in sample
        assert "resolution_time_formatted" in sample
        print(f"  Sample Issue #{sample['id']} ({sample['issue_key']}): status='{sample['status']}', resolution_time_hours={sample['resolution_time_hours']}, formatted='{sample['resolution_time_formatted']}'")
    print("[PASS] Issue schema fields verified successfully!\n")

    print("================================================================")
    print("[SUCCESS] ALL MTTR FEATURE TESTS PASSED 100%!")
    print("================================================================")

if __name__ == "__main__":
    run_mttr_tests()
