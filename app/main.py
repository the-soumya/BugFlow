from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.routers import auth, project, issue, triage, collaboration, sprint
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
    title="BugFlow - Software Issue Tracking & Resolution Platform",
    description="Layered Issue Tracking Platform: Core Foundation and Agile Workflow, Smart Triage & Team Collaboration Engine",
    version="2.0.0",
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

# Catch-all route to serve the SPA index.html
@app.get("/")
def serve_spa():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "BugFlow Backend is running. Frontend static/index.html is missing."}
