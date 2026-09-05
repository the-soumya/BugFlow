from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest, LoginRequest
from app.security import get_password_hash, verify_password, create_access_token
from app.exceptions import DuplicateKey, Unauthorized

def register_user(db: Session, request: RegisterRequest) -> User:
    # Check duplicate email
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise DuplicateKey(f"Email {request.email} is already registered")

    hashed_password = get_password_hash(request.password)
    user = User(
        name=request.name,
        email=request.email,
        password=hashed_password,
        role=request.role,
        active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def authenticate_user(db: Session, request: LoginRequest) -> str:
    user = db.query(User).filter(User.email == request.email, User.active == True).first()
    if not user or not verify_password(request.password, user.password):
        raise Unauthorized("Invalid email or password")

    # Generate token payload
    token = create_access_token(data={"sub": user.email, "role": user.role.value, "name": user.name, "id": user.id})
    return token
