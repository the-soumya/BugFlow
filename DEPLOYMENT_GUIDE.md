# 🚀 BugFlow Platform — Enterprise Deployment & Operations Guide

This guide provides end-to-end instructions for deploying, configuring, monitoring, and scaling the **BugFlow Enterprise Issue Tracking & Resolution Platform** in production and staging environments.

---

## 🏛️ 1. Architecture Overview

BugFlow is built as a high-throughput, microservice-ready architecture comprising:
- **Client Tier**: Responsive Single-Page Application (HTML5 / Vanilla CSS / ES6+ JavaScript) served through FastAPI static mount or CDN/Nginx.
- **Application Tier**: FastAPI (Python 3.11/3.12) running under Uvicorn ASGI worker pools with connection reuse.
- **Persistence Tier**: PostgreSQL 15 with composite B-tree indexing and optimized connection pooling (`pool_size=20`, `max_overflow=10`).
- **Telemetry & Health**: Live JSON heartbeat probe at `/health` monitoring database connectivity and connection pool metrics.

---

## 🐳 2. Single-Command Docker Deployment (Recommended)

BugFlow includes production-grade container specifications with `Dockerfile` and `docker-compose.yml`.

### Prerequisites
- Docker Engine 24.0+
- Docker Compose v2.20+

### Step-by-Step Launch
1. **Clone and enter the repository:**
   ```bash
   git clone https://github.com/the-soumya/BugFlow.git
   cd BugFlow
   ```

2. **Start the containers:**
   ```bash
   docker compose up --build -d
   ```

3. **Verify running containers:**
   ```bash
   docker compose ps
   ```
   Expected output:
   ```
   NAME               IMAGE                COMMAND                  SERVICE   STATUS
   bugflow-postgres   postgres:15-alpine   "docker-entrypoint.s…"   db        Up (healthy)
   bugflow-api        bugflow-web          "uvicorn app.main:ap…"   web       Up (healthy)
   ```

4. **Access the application:**
   - **Web UI & Dashboard**: `http://localhost:8000`
   - **Interactive OpenAPI Swagger Docs**: `http://localhost:8000/docs`
   - **Alternative ReDoc Reference**: `http://localhost:8000/redoc`
   - **Platform Health Probe**: `http://localhost:8000/health`

---

## ⚙️ 3. Environment Configuration

Configure production environment parameters in a `.env` file or orchestrator secrets (Kubernetes Secrets, AWS SSM, Docker Swarm):

| Variable | Description | Default / Example | Required |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection URI | `postgresql://postgres:1601@localhost:5432/bugflow` | **Yes** |
| `JWT_SECRET` | Cryptographic secret for signing JWTs | `d2bdf7859b897931b2694f57c5eb6ef80e81e352ef29b87fcf30f81dcd3f89ee` | **Yes** |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` | No |
| `JWT_EXPIRATION_MINUTES` | Token validity duration | `120` (2 hours) | No |
| `POSTGRES_USER` | PostgreSQL superuser username | `postgres` | **Yes** |
| `POSTGRES_PASSWORD` | PostgreSQL superuser password | `1601` | **Yes** |
| `POSTGRES_DB` | Primary database name | `bugflow` | **Yes** |

---

## 🏊 4. Database Connection Pooling & Tuning

BugFlow's database engine in [app/database.py](file:///c:/Users/Soumya/OneDrive/Desktop/Milestone1/app/database.py) is pre-configured with enterprise pooling:

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=20,          # Base steady-state connection pool size
    max_overflow=10,       # Burst capacity during peak loads (total 30 per worker)
    pool_pre_ping=True,    # Actively verifies connection health before checkout
    pool_recycle=3600      # Recycles connections every hour to avoid stale sockets
)
```

### PostgreSQL Server Settings (`postgresql.conf` recommendations)
For high-concurrency environments handling 50,000+ issues:
```ini
max_connections = 125
shared_buffers = 256MB
effective_cache_size = 768MB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
```

---

## ⚡ 5. Database Indexes Verification

BugFlow implements composite indexes in [app/models/issue.py](file:///c:/Users/Soumya/OneDrive/Desktop/Milestone1/app/models/issue.py) to guarantee sub-millisecond query execution:

- `idx_issue_project_status` on `(project_id, status)` — Optimizes project dashboard and Kanban boards.
- `idx_issue_assignee_status` on `(assignee_id, status)` — Powers developer workload matrix queries.
- `idx_issue_created_at` on `(created_at)` — Enables rapid 14-day defect trend time-series grouping.
- `idx_issue_sprint_status` on `(sprint_id, status)` — Accelerates active sprint backlog filtering.

To verify existing indexes in PostgreSQL:
```sql
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'issues';
```

---

## 🩺 6. Health Checks & Latency Monitoring

BugFlow exposes a live heartbeat endpoint:
```http
GET /health
```

Sample 200 OK Response:
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

Target SLA: **< 300 ms response time** across all standard read and write workloads.

---

## 🔄 7. Backup and Disaster Recovery

### Automated Database Backup
```bash
# Backup
docker exec -t bugflow-postgres pg_dump -U postgres bugflow > bugflow_backup_$(date +%Y%m%d_%H%M%S).sql

# Restore
docker exec -i bugflow-postgres psql -U postgres bugflow < bugflow_backup_20261001.sql
```

---

## 🌐 8. Production Reverse Proxy (Nginx Configuration)

```nginx
server {
    listen 80;
    server_name bugflow.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name bugflow.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/bugflow.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bugflow.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
