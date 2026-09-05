from pydantic import BaseModel, Field
from typing import Optional, List
from app.models.issue import IssuePriority, IssueSeverity

class TriageRecommendationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    severity: Optional[str] = "MEDIUM"
    category: Optional[str] = "General"

class DeveloperRecommendation(BaseModel):
    developer_id: int
    name: str
    email: str
    skills: str
    match_percentage: int
    active_tasks: int
    rationale: str

class TriageRecommendationResponse(BaseModel):
    priority_score: float
    recommended_priority: str
    severity: str
    severity_weight: int
    category: str
    category_urgency_weight: int
    formula: str
    recommended_developers: List[DeveloperRecommendation]
