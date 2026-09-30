from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.routers import auth, project, issue, triage, collaboration, sprint, webhook, analytics, export
from app.exceptions import setup_exception_handlers

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed database at startup if needed
    from app.seed import seed_data
    try:
        seed_data()
    except Exception as e:
        print(f" LIFESPAN: Failed to run startup seed: {e}")
    yield

# Initialize FastAPI App
app = FastAPI(
    title="BugFlow - Enterprise Issue Tracking & Resolution Platform",
    description="High-Performance Issue Tracking: Core Foundation, Agile Collaboration, Quality Metrics, CI/CD Webhooks & Database Optimization",
    version="4.0.0",
    lifespan=lifespan
)

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register custom global exception handlers
setup_exception_handlers(app)

# Layer 1: Core Platform Routers (Auth, Projects, Issues)
app.include_router(auth.router)
app.include_router(project.router)
app.include_router(issue.router)

# Layer 2: Agile Workflow & Collaboration Routers (Triage, Collaboration, Sprints)
app.include_router(triage.router)
app.include_router(collaboration.router)
app.include_router(sprint.router)

# Layer 3: Analytics, Automated CI/CD Webhooks & Export Routers
app.include_router(webhook.router)
app.include_router(analytics.router)
app.include_router(export.router)

# Mount the static directory for the SPA frontend
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount uploads directory for screenshots and error logs
uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)

app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Health check endpoint for containerization, uptime monitoring, and SLA verification
@app.get("/health")
def health_check():
    from app.database import engine
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_type = "postgresql" if "postgresql" in str(engine.url) else "sqlite"
        return {
            "status": "healthy",
            "database": db_type,
            "version": "4.0.0",
            "pool": {
                "pool_size": 20,
                "max_overflow": 10,
                "pool_pre_ping": True
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

# SPA Route serving for normal URLs (Dashboard, Issues, Sprints, Analytics, etc.)
@app.get("/")
@app.get("/dashboard")
@app.get("/issues")
@app.get("/my-issues")
@app.get("/report-issue")
@app.get("/resolution-assistance")
@app.get("/sprints")
@app.get("/projects")
@app.get("/team")
@app.get("/reports")
@app.get("/analytics")
@app.get("/optimization")
def serve_spa():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "BugFlow Backend is running. Frontend static/index.html is missing."}

# Published Documentation Endpoints (Milestone 4 Requirement)
@app.get("/deployment-guide")
def get_deployment_guide():
    guide_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "DEPLOYMENT_GUIDE.md")
    return FileResponse(guide_path, media_type="text/markdown")

@app.get("/user-guide")
def get_user_guide():
    guide_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "USER_GUIDE.md")
    return FileResponse(guide_path, media_type="text/markdown")

@app.get("/api-docs-file")
def get_api_docs_file():
    docs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "API_DOCUMENTATION.md")
    return FileResponse(docs_path, media_type="text/markdown")


