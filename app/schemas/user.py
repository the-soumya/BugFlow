from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from app.models.user import UserRole

class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)
    role: UserRole = UserRole.USER
    skills: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: UserRole
    active: bool
    skills: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserMinResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: UserRole
    skills: Optional[str] = None

    class Config:
        from_attributes = True
