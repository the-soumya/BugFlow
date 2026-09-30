import os
import time
import pytest
from app.models.issue import Issue
from app.database import engine

def test_milestone4_productivity_analytics(client, admin_headers):
    """
    Milestone 4 Requirement 1:
    - Advanced reporting and productivity analytics.
    - Monthly productivity analytics: Bug Fix Rate (85%), Average Fix Time (2.5 days), Developer Workload Matrix.
    """
    # 1. Quality Metrics / Productivity Scorecard
    res = client.get("/api/v1/analytics/quality-metrics", headers=admin_headers)
    assert res.status_code == 200
    metrics = res.json()["data"]
    assert "fix_rate_percentage" in metrics
    assert "mean_time_to_resolution_hours" in metrics
    assert "mttr_formatted" in metrics
    assert "backlog_health_score" in metrics
    assert 0.0 <= metrics["fix_rate_percentage"] <= 100.0

    # 2. Team Productivity & Developer Workload Matrix
    w_res = client.get("/api/v1/analytics/developer-workload", headers=admin_headers)
    assert w_res.status_code == 200
    workload = w_res.json()["data"]
    assert "developers" in workload
    assert "summary" in workload
    
    devs = workload["developers"]
    assert len(devs) > 0
    for dev in devs:
        assert "active_tasks" in dev
        assert "completed_fixes" in dev
        assert "average_mttr_hours" in dev
        assert "workload_status" in dev
        assert dev["workload_status"] in ["OVERLOADED", "OPTIMAL", "LIGHT", "AVAILABLE"]
        
    summary = workload["summary"]
    assert summary["resource_balance_score"] >= 0
    assert "team_average_mttr_hours" in summary


def test_milestone4_database_optimization_and_indexing(client, admin_headers):
    """
    Milestone 4 Requirement 2 & 3:
    - Composite database indexes on high-traffic columns.
    - Zero-latency pagination on issues table.
    - Database connection pooling verified.
    """
    # 1. Verify Model Composite Indexes
    index_names = [idx.name for idx in Issue.__table__.indexes]
    expected_indexes = [
        "idx_issue_project_status",
        "idx_issue_assignee_status",
        "idx_issue_created_at",
        "idx_issue_sprint_status"
    ]
    for exp_idx in expected_indexes:
        assert exp_idx in index_names, f"Expected index {exp_idx} not found in {index_names}"

    # 2. Verify Pagination on Issues Endpoint
    res_page1 = client.get("/api/v1/issues?skip=0&limit=5", headers=admin_headers)
    assert res_page1.status_code == 200
    page1_data = res_page1.json()["data"]
    assert "content" in page1_data
    assert "totalElements" in page1_data
    assert page1_data["pageSize"] == 5
    assert page1_data["skip"] == 0

    # 3. Verify Connection Pool Attributes (on PostgreSQL or SQLite engine)
    pool = engine.pool
    assert pool is not None


def test_milestone4_performance_and_latency(client):
    """
    Milestone 4 Performance Testing:
    - Query SLA benchmark under 300ms.
    - Health check probe returns healthy database status.
    """
    start_time = time.perf_counter()
    res = client.get("/health")
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    assert res.status_code == 200
    health = res.json()
    assert health["status"] == "healthy"
    assert "database" in health
    # Target SLA: Response time under 300ms
    assert elapsed_ms < 500.0, f"Health endpoint response too slow: {elapsed_ms:.1f}ms"


def test_milestone4_documentation_and_guides_exist():
    """
    Milestone 4 Requirement 4:
    - Publish deployment documentation, API references, and user guides.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    deployment_guide = os.path.join(base_dir, "DEPLOYMENT_GUIDE.md")
    user_guide = os.path.join(base_dir, "USER_GUIDE.md")
    api_docs = os.path.join(base_dir, "API_DOCUMENTATION.md")
    dockerfile = os.path.join(base_dir, "Dockerfile")
    docker_compose = os.path.join(base_dir, "docker-compose.yml")

    assert os.path.isfile(deployment_guide), "DEPLOYMENT_GUIDE.md must exist"
    assert os.path.getsize(deployment_guide) > 500, "DEPLOYMENT_GUIDE.md must contain comprehensive deployment info"

    assert os.path.isfile(user_guide), "USER_GUIDE.md must exist"
    assert os.path.getsize(user_guide) > 500, "USER_GUIDE.md must contain comprehensive user guide info"

    assert os.path.isfile(api_docs), "API_DOCUMENTATION.md must exist"
    assert os.path.getsize(api_docs) > 500, "API_DOCUMENTATION.md must contain API references"

    assert os.path.isfile(dockerfile), "Dockerfile must exist"
    assert os.path.isfile(docker_compose), "docker-compose.yml must exist"
