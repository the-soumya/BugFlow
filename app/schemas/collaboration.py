from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.schemas.user import UserMinResponse

class CommentCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)

class CommentResponse(BaseModel):
    id: int
    issue_id: int
    user_id: Optional[int]
    content: str
    created_at: datetime
    user: Optional[UserMinResponse] = None

    class Config:
        from_attributes = True

class AttachmentResponse(BaseModel):
    id: int
    issue_id: int
    user_id: Optional[int]
    filename: str
    file_path: str
    file_type: Optional[str]
    file_size: int
    uploaded_at: datetime
    user: Optional[UserMinResponse] = None

    class Config:
        from_attributes = True
