import pytest

def test_quality_metrics_and_mttr_calculation(client, admin_headers):
    res = client.get("/api/v1/analytics/quality-metrics", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    
    assert "fix_rate_percentage" in data
    assert "mean_time_to_resolution_hours" in data
    assert "defect_leakage_rate_percentage" in data
    assert "backlog_health_score" in data
    assert 0.0 <= data["fix_rate_percentage"] <= 100.0
    assert 0 <= data["backlog_health_score"] <= 100
    assert isinstance(data["mean_time_to_resolution_hours"], (int, float))

def test_plotly_chart_generation(client, admin_headers):
    res = client.get("/api/v1/analytics/plotly-charts", headers=admin_headers)
    assert res.status_code == 200
    charts = res.json()["data"]
    
    assert "trend_chart" in charts
    assert "severity_chart" in charts
    assert "workflow_chart" in charts
    assert "mttr_chart" in charts
    assert "ttr_chart" in charts
    
    # Verify trend chart structure
    trend = charts["trend_chart"]
    assert "data" in trend and "layout" in trend
    assert len(trend["data"]) >= 2
    
    # Verify severity pie chart structure
    sev = charts["severity_chart"]
    assert sev["data"][0]["type"] == "pie"
    assert sev["data"][0]["hole"] > 0

def test_developer_workload_matrix(client, admin_headers):
    res = client.get("/api/v1/analytics/developer-workload", headers=admin_headers)
    assert res.status_code == 200
    workload_data = res.json()["data"]
    
    assert "developers" in workload_data
    assert "summary" in workload_data
    devs = workload_data["developers"]
    assert len(devs) > 0
    
    # Validate each developer item
    for d in devs:
        assert "name" in d
        assert "team" in d
        assert "active_tasks" in d
        assert "completed_fixes" in d
        assert "average_mttr_hours" in d
        assert "workload_status" in d
        assert d["workload_status"] in ["OVERLOADED", "OPTIMAL", "LIGHT", "AVAILABLE"]
    
    summary = workload_data["summary"]
    assert "total_developers" in summary
    assert "total_active_tasks" in summary
    assert "team_average_mttr_hours" in summary

def test_health_check_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    health = res.json()
    assert health["status"] == "healthy"
    assert "database" in health
    assert health["database"] in ["postgresql", "sqlite"]
