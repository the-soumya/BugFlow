from pydantic import BaseModel, EmailStr, Field
from app.models.user import UserRole

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    role: UserRole = UserRole.USER

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

class LoginResponse(BaseModel):
    token: str
    type: str = "Bearer"
