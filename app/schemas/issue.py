from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict
from app.models.issue import IssueType, WorkflowState, IssuePriority, IssueSeverity
from app.schemas.user import UserMinResponse

class IssueCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    issue_type: IssueType = IssueType.BUG
    priority: IssuePriority = IssuePriority.MEDIUM
    severity: IssueSeverity = IssueSeverity.MEDIUM
    category: Optional[str] = "General"
    sprint_id: Optional[int] = None
    assignee_id: Optional[int] = None

class IssueUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    issue_type: Optional[IssueType] = None
    priority: Optional[IssuePriority] = None
    severity: Optional[IssueSeverity] = None
    category: Optional[str] = None
    sprint_id: Optional[int] = None

class AssignIssueRequest(BaseModel):
    assignee_id: Optional[int] = None

class StatusUpdateRequest(BaseModel):
    status: WorkflowState

class IssueResponse(BaseModel):
    id: int
    issue_key: str
    title: str
    description: Optional[str]
    issue_type: IssueType
    status: WorkflowState
    priority: IssuePriority
    severity: IssueSeverity
    category: Optional[str] = "General"
    priority_score: Optional[float] = None
    project_id: int
    reporter_id: Optional[int]
    assignee_id: Optional[int]
    sprint_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    resolution_time_hours: Optional[float] = None
    resolution_time_formatted: Optional[str] = None
    
    # Embedded user details
    reporter: Optional[UserMinResponse] = None
    assignee: Optional[UserMinResponse] = None

    class Config:
        from_attributes = True

class IssueSummaryResponse(BaseModel):
    totalIssues: int
    openIssues: int
    inProgressIssues: int
    resolvedIssues: int
    closedIssues: int
    criticalIssues: int
    highPriorityIssues: int
    statusCounts: Dict[str, int]
    priorityCounts: Dict[str, int]
    severityCounts: Dict[str, int]
    typeCounts: Dict[str, int]
