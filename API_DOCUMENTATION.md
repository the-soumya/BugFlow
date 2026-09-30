# 📡 BugFlow API Documentation & Specification

Complete endpoint references, payload specifications, and sample responses for all four BugFlow platform modules.

---

## 🔐 1. Authentication & User Management

### `POST /api/auth/register`
Creates a new user account with hashed password.

**Request:**
```json
{
  "name": "Alice Smith",
  "email": "alice@bugflow.com",
  "password": "password123",
  "role": "DEVELOPER",
  "team": "Frontend UI",
  "skills": "React, TypeScript, CSS"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "message": "User registered successfully",
  "data": {
    "id": 3,
    "name": "Alice Smith",
    "email": "alice@bugflow.com",
    "role": "DEVELOPER",
    "team": "Frontend UI",
    "active": true
  }
}
```

---

### `POST /api/auth/login`
Authenticates user credentials and returns a signed JWT access token.

**Request:**
```json
{
  "email": "admin@bugflow.com",
  "password": "password123"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "type": "Bearer"
  }
}
```

---

## ⚡ 2. Health & Performance Endpoints

### `GET /health`
Returns system status, active database engine, and connection pool parameters.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "database": "postgresql",
  "version": "4.0.0",
  "pool": {
    "pool_size": 20,
    "max_overflow": 10,
    "pool_pre_ping": true
  }
}
```

---

## 🧑‍💼 3. Analytics & Developer Workload Matrix

### `GET /api/v1/analytics/developer-workload`
Returns developer task loads, active bugs (`IN_PROGRESS`/`CODE_REVIEW`), completed fixes, individual MTTR, and Resource Balance Indicators.

**Query Parameters:**
- `project_id` *(optional, int)*: Filter by project ID.

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Developer workload matrix retrieved successfully",
  "data": {
    "developers": [
      {
        "id": 3,
        "name": "Alice Smith",
        "email": "alice@bugflow.com",
        "role": "DEVELOPER",
        "team": "Frontend UI",
        "skills": "React, TypeScript, CSS3",
        "active_tasks": 2,
        "in_progress_tasks": 2,
        "completed_fixes": 2,
        "average_mttr_hours": 15.0,
        "average_mttr_formatted": "15.0 hrs",
        "workload_status": "OPTIMAL",
        "balance_color": "#10b981",
        "recommendation": "Workload balanced at target capacity",
        "active_issue_keys": ["BUG-5", "BUG-8"]
      },
      {
        "id": 2,
        "name": "John Doe",
        "email": "pm@bugflow.com",
        "role": "PROJECT_MANAGER",
        "team": "Backend Engineering",
        "skills": "Python, PostgreSQL, Architecture",
        "active_tasks": 1,
        "in_progress_tasks": 1,
        "completed_fixes": 1,
        "average_mttr_hours": 42.0,
        "average_mttr_formatted": "1.8 days",
        "workload_status": "LIGHT",
        "balance_color": "#3b82f6",
        "recommendation": "Available for sprint backlog assignment",
        "active_issue_keys": ["BUG-3"]
      }
    ],
    "summary": {
      "total_developers": 6,
      "total_active_tasks": 5,
      "total_completed_fixes": 4,
      "team_average_mttr_hours": 21.4,
      "team_average_mttr_formatted": "21.4 hrs",
      "resource_balance_score": 88,
      "balance_health": "OPTIMAL_BALANCE"
    }
  }
}
```

---

### `GET /api/v1/analytics/quality-metrics`
Returns Software Quality Scorecard metrics.

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Quality metrics calculated successfully",
  "data": {
    "fix_rate_percentage": 50.0,
    "mean_time_to_resolution_hours": 21.4,
    "mttr_formatted": "21.4 hours",
    "defect_leakage_rate_percentage": 12.5,
    "backlog_health_score": 88,
    "health_status": "EXCELLENT",
    "mttr_sla_compliance_rate": 87.5
  }
}
```

---

## 🐞 4. Issues & Database Pagination

### `GET /api/v1/issues`
Lists issues with high-performance composite index querying, filtering, and skip/limit pagination.

**Query Parameters:**
- `skip` *(optional, int)*: Number of records to skip (e.g. `0`, `20`, `40`).
- `limit` *(optional, int)*: Page limit (default `20`, max `100`).
- `status` *(optional, string)*: `REPORTED`, `TRIAGED`, `IN_PROGRESS`, `QA_VERIFICATION`, `RESOLVED`, `CLOSED`.
- `priority` *(optional, string)*: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`, `URGENT`.
- `severity` *(optional, string)*: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
- `assignee` *(optional, int)*: User ID of assignee.

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Issues retrieved successfully",
  "data": {
    "content": [
      {
        "id": 2,
        "issue_key": "BUG-2",
        "title": "Error on Login with Special Characters in Password",
        "status": "IN_PROGRESS",
        "priority": "URGENT",
        "severity": "CRITICAL",
        "category": "Security",
        "priority_score": 12.0,
        "assignee": {
          "id": 5,
          "name": "Alex Rivera",
          "email": "dev@bugflow.com"
        }
      }
    ],
    "totalElements": 8,
    "totalPages": 1,
    "pageNumber": 0,
    "pageSize": 20,
    "skip": 0,
    "limit": 20
  }
}
```

---

## 🏃 5. Sprints & Agile Backlog

### `POST /api/v1/sprints/`
Creates a new sprint.

**Request:**
```json
{
  "project_id": 1,
  "name": "Sprint 3 - Core Hardening",
  "goal": "Improve automated test coverage and database pooling resilience",
  "start_date": "2026-10-01T00:00:00Z",
  "end_date": "2026-10-15T00:00:00Z"
}
```

### `POST /api/v1/sprints/{id}/add-issue/{issue_id}`
Moves a backlog bug into the designated sprint.

### `PUT /api/v1/sprints/{id}/status`
Transitions sprint status (`PLANNING`, `ACTIVE`, `COMPLETED`) and calculates team velocity upon completion.

---

## 🤖 6. CI/CD Git Webhooks

### `POST /api/v1/webhooks/git`
Parses incoming Git commit messages for issue IDs and auto-transitions them to `QA_VERIFICATION`.

**Request:**
```json
{
  "commit_message": "Merge PR #45: fixes #2 login password crash",
  "commit_hash": "a7f8c92",
  "author": "CI/CD Bot"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Processed 1 issue transitions from commit message",
  "data": {
    "commit_hash": "a7f8c92",
    "updated_issues": [
      {
        "id": 2,
        "issue_key": "BUG-2",
        "new_status": "QA_VERIFICATION"
      }
    ]
  }
}
```
