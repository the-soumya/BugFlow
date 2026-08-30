from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    project_key: str = Field(..., min_length=2, max_length=10, pattern=r"^[A-Z0-9]+$")

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    project_key: str
    active: bool
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[int]

    class Config:
        from_attributes = True
