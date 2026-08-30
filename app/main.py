from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.routers import auth, project, issue
from app.exceptions import setup_exception_handlers

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed database at startup if empty
    from app.seed import seed_data
    try:
        seed_data()
    except Exception as e:
        print(f" LIFESPAN: Failed to run startup seed: {e}")
    yield

# Initialize FastAPI App
app = FastAPI(
    title="BugFlow - Issue Tracking & Resolution Platform",
    description="Milestone 1 API and Dashboard Platform",
    version="1.0.0",
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

# Include routers
app.include_router(auth.router)
app.include_router(project.router)
app.include_router(issue.router)

# Mount the static directory for the SPA frontend
# We create it first to avoid any startup crashes
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Catch-all route to serve the SPA index.html
@app.get("/")
def serve_spa():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "BugFlow Backend is running. Frontend static/index.html is missing."}
