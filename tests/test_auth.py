import pytest
from app.security import get_password_hash, verify_password, create_access_token
from app.models.user import User, UserRole

def test_password_hashing_bcrypt():
    password = "SecurePassword123!"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_token_issuance_and_decoding():
    token = create_access_token({"sub": "admin@bugflow.com", "role": "ADMIN"})
    assert isinstance(token, str)
    assert len(token) > 20

def test_user_registration_and_login_flow(client, db):
    # 1. Register a new developer
    reg_email = "newdev@bugflow.com"
    # Ensure not existing
    db.query(User).filter(User.email == reg_email).delete()
    db.commit()

    reg_payload = {
        "name": "New Developer",
        "email": reg_email,
        "password": "Password123!",
        "role": "DEVELOPER",
        "skills": "Python, React, Docker"
    }
    res = client.post("/api/auth/register", json=reg_payload)
    assert res.status_code in [200, 201]
    data = res.json()
    assert data["success"] is True
    assert data["data"]["email"] == reg_email
    assert data["data"]["role"] == "DEVELOPER"

    # 2. Duplicate registration should be rejected
    dup_res = client.post("/api/auth/register", json=reg_payload)
    assert dup_res.status_code in [400, 409]

    # 3. Login with correct credentials
    login_res = client.post("/api/auth/login", json={
        "email": reg_email,
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["success"] is True
    assert "token" in login_data["data"]

    # 4. Login with invalid password
    bad_login = client.post("/api/auth/login", json={
        "email": reg_email,
        "password": "WrongPassword"
    })
    assert bad_login.status_code in [400, 401]

def test_role_access_control(client, admin_headers, dev_headers, tester_headers, user_headers):
    # Authenticated user can fetch users list
    res_admin = client.get("/api/auth/users", headers=admin_headers)
    assert res_admin.status_code == 200
    users = res_admin.json()["data"]
    assert len(users) >= 3

    # Dev and Tester roles can also access authenticated users list
    res_dev = client.get("/api/auth/users", headers=dev_headers)
    assert res_dev.status_code == 200

    res_tester = client.get("/api/auth/users", headers=tester_headers)
    assert res_tester.status_code == 200

    # Unauthenticated request is rejected
    res_unauth = client.get("/api/auth/users")
    assert res_unauth.status_code == 401
