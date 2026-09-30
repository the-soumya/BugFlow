# 🐞 BugFlow — Enterprise Software Issue Tracking & Resolution Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.112.2-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue.svg?style=flat&logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg?style=flat&logo=postgresql)](https://postgresql.org)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.32-d71f00.svg?style=flat)](https://sqlalchemy.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=flat&logo=docker)](https://docker.com)
[![Pytest](https://img.shields.io/badge/Tests-16%20Passed%20(100%25)-brightgreen.svg?style=flat&logo=pytest)](https://pytest.org)

**BugFlow** is a modern, high-performance, full-stack issue tracking and agile engineering management platform built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.0**, and an interactive **Single-Page Application (SPA)** frontend.

---

## 🏛️ System Architecture

```mermaid
graph TD
    Client["💻 Client Frontend SPA<br>(HTML5 / CSS3 / Vanilla JS)"]
    API["⚡ FastAPI Application Server<br>(Uvicorn Worker Pool)"]
    Auth["🔐 JWT Security & RBAC<br>(Admin / PM / Dev / Tester)"]
    Triage["🧠 Smart Triage & ML Scoring<br>(Severity × Urgency Matrix)"]
    Analytics["📊 Quality Analytics Engine<br>(MTTR, Fix Rate, Plotly, PDF/CSV)"]
    Workload["🧑‍💼 Developer Productivity Matrix<br>(Workload & Balance Index)"]
    DBPool["🏊 Connection Pool<br>(size=20, max_overflow=10)"]
    Postgres[("🐘 PostgreSQL 15 Database<br>(50,000+ Issues Capacity)")]
    Indexes["⚡ Composite Indexes<br>(project_id, status), (assignee_id, status), (created_at)"]

    Client -->|REST & Webhooks| API
    API --> Auth
    API --> Triage
    API --> Analytics
    API --> Workload
    API --> DBPool
    DBPool --> Postgres
    Postgres --- Indexes
```

---

## 🚀 Key Modules & Milestones

### 1. 🏗️ Milestone 1: Core Issue Tracking Foundation
- **Role-Based Access Control (RBAC)**: `ADMIN`, `PROJECT_MANAGER`, `DEVELOPER`, `TESTER`, `USER`.
- **BCrypt Password Security & JWT Token Authentication**.
- **Issue Lifecycle Engine**: Unique issue keys (`BUG-1`, `BUG-2`), priorities, severities, and full CRUD operations.

### 2. 🚀 Milestone 2: Agile Collaboration & Triage
- **Smart Priority Scoring Math**: $Score = \text{Severity Weight} \times \text{Category Urgency Weight}$.
- **Smart Developer Matcher**: Text keyword analysis and skill-domain heuristics with workload load-balancing.
- **Kanban & Sprints Workflow**: Sprint management, backlog movement, and velocity calculations.
- **Audit Trails & Activity Streams**: Comprehensive event tracking on status transitions and assignments.

### 3. 📈 Milestone 3: Quality Analytics & CI/CD Webhooks
- **Automated Git Commit Webhooks**: Auto-transitions bugs from commit messages (`fixes #2`) with commit hashes and author audit logs.
- **Software Quality Scorecard**: Fix Rate Percentage, MTTR (Mean Time to Resolution in hours/days), Defect Leakage Rate, and Backlog Health Score.
- **Interactive Plotly Visualizations**: 14-day defect trends, severity distribution, and workflow pipeline charts.
- **One-Click Exporters**: Executive PDF Quality Reports and Excel-Ready UTF-8 BOM CSV exports.

### 4. ⚡ Milestone 4: Database Speed Optimization & Workload Matrix
- **Developer Productivity Matrix**: Real-time tracking of active tasks, completed fixes, individual MTTR, and Resource Balance Indicators (`OVERLOADED`, `OPTIMAL`, `AVAILABLE`).
- **Database Composite Indexing**: Sub-millisecond queries on 50,000+ rows via `(project_id, status)`, `(assignee_id, status)`, and `(created_at)`.
- **Connection Pooling**: Reusable connection pool (`pool_size=20`, `max_overflow=10`, `pool_pre_ping=True`).
- **Zero-Latency Pagination**: Seamless `skip` and `limit` support across all issue query endpoints.
- **Comprehensive Pytest Suite**: 100% test coverage across authentication, issue lifecycle, sprints, analytics, and health checks.

---

## ⚡ Quick Start (Docker - Recommended)

Run both the FastAPI server and PostgreSQL 15 database container with one command:

```bash
docker compose up --build
```

- **SPA Application**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🛠️ Local Development Setup (Without Docker)

### 1. Prerequisites
- Python 3.11+
- PostgreSQL 15 (or SQLite for local mock testing)

### 2. Install Dependencies
```bash
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure Environment
Set `DATABASE_URL` and `JWT_SECRET` in your environment (or use default configuration):
```powershell
$env:DATABASE_URL="postgresql://postgres:1601@localhost:5432/bugflow"
$env:JWT_SECRET="d2bdf7859b897931b2694f57c5eb6ef80e81e352ef29b87fcf30f81dcd3f89ee"
```

### 4. Seed Database & Start Server
```bash
python -m app.seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🧪 Running Automated Pytest Suite

Run all automated unit and integration tests:

```bash
pytest tests/ -v
```

All 16 test cases across `test_auth.py`, `test_issues.py`, `test_sprints.py`, `test_analytics.py`, `test_milestone3.py`, and `test_agile_collaboration.py` will pass with 100% green checkmarks.

---

## 🔑 Default Seed Accounts

| Name | Email | Password | Role | Team |
| :--- | :--- | :--- | :--- | :--- |
| **System Administrator** | `admin@bugflow.com` | `password123` | `ADMIN` | DevOps & SRE |
| **John Doe** | `pm@bugflow.com` | `password123` | `PROJECT_MANAGER` | Backend Engineering |
| **Alice Smith** | `alice@bugflow.com` | `password123` | `DEVELOPER` | Frontend UI |
| **Bruce Wayne** | `tester@bugflow.com` | `password123` | `TESTER` | Security & QA |
| **Alex Rivera** | `dev@bugflow.com` | `password123` | `DEVELOPER` | Backend Engineering |
| **Taylor Kim** | `user@bugflow.com` | `password123` | `USER` | Frontend UI |

---

## 📖 API Documentation Reference

Refer to [API_DOCUMENTATION.md](file:///c:/Users/Soumya/OneDrive/Desktop/Milestone1/API_DOCUMENTATION.md) for full endpoint specifications, request/response schemas, and curl examples.
