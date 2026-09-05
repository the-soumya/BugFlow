from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from app.models.sprint import SprintStatus

class SprintCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    goal: Optional[str] = Field(None, max_length=500)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    project_id: Optional[int] = None

class SprintStatusUpdateRequest(BaseModel):
    status: SprintStatus

class SprintResponse(BaseModel):
    id: int
    project_id: Optional[int]
    name: str
    goal: Optional[str]
    start_date: datetime
    end_date: Optional[datetime]
    status: SprintStatus
    velocity: int
    created_at: datetime
    updated_at: datetime

    # Summary metrics
    total_issues: int = 0
    resolved_issues: int = 0
    progress_percentage: float = 0.0

    class Config:
        from_attributes = True

class SprintSummaryResponse(BaseModel):
    sprints: List[SprintResponse]
    total_sprints: int
    active_sprints: int
    total_backlog_issues: int
