from typing import List

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.models.user import User

from app.database import get_db
from app.schemas import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    UserResponse,
    ApiResponse
)
from app.schemas.user import UserMinResponse
from app.services import auth as auth_service
from app.security import get_current_user


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


# ============================================================
# REGISTER
# ============================================================

@router.post(
    "/register",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED
)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    user = auth_service.register_user(db, request)

    user_response = UserResponse.model_validate(user)

    return ApiResponse(
        success=True,
        message="User registered successfully",
        data=user_response
    )


# ============================================================
# NORMAL FRONTEND LOGIN
# ============================================================

@router.post(
    "/login",
    response_model=ApiResponse[LoginResponse]
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    token = auth_service.authenticate_user(
        db,
        request
    )

    return ApiResponse(
        success=True,
        message="Login successful",
        data=LoginResponse(
            token=token,
            type="Bearer"
        )
    )


# ============================================================
# SWAGGER / OAUTH2 LOGIN
# ============================================================

@router.post("/token")
def swagger_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 password-flow endpoint used by Swagger.

    Swagger sends:
        username = admin@bugflow.com
        password = password123

    The username field is treated as the user's email.
    """

    login_request = LoginRequest(
        email=form_data.username,
        password=form_data.password
    )

    access_token = auth_service.authenticate_user(
        db,
        login_request
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# ============================================================
# GET USERS
# ============================================================

@router.get(
    "/users",
    response_model=ApiResponse[List[UserMinResponse]]
)
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    users = (
        db.query(User)
        .filter(User.active == True)
        .all()
    )

    response_data = [
        UserMinResponse.model_validate(user)
        for user in users
    ]

    return ApiResponse(
        success=True,
        message="Users retrieved successfully",
        data=response_data
    )