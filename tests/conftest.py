import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal, engine, Base
from app.seed import seed_data
from app.models.user import User, UserRole
from app.security import create_access_token

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Ensure database tables, indexes, and initial seed data are populated."""
    seed_data()
    yield

@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient instance."""
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="function")
def db():
    """Yields a database session for direct inspection/assertions."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="session")
def admin_headers():
    token = create_access_token({"sub": "admin@bugflow.com", "role": "ADMIN"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="session")
def dev_headers():
    token = create_access_token({"sub": "dev@bugflow.com", "role": "DEVELOPER"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="session")
def tester_headers():
    token = create_access_token({"sub": "tester@bugflow.com", "role": "TESTER"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="session")
def user_headers():
    token = create_access_token({"sub": "user@bugflow.com", "role": "USER"})
    return {"Authorization": f"Bearer {token}"}
