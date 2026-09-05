from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.triage import (
    TriageRecommendationRequest,
    TriageRecommendationResponse,
    DeveloperRecommendation
)
from app.schemas.response import ApiResponse
from app.services import triage as triage_service
from app.security import get_current_user
from app.models.user import User

router = APIRouter(
    prefix="/api/v1/issues",
    tags=["Smart Triage & Recommendations"]
)

@router.post(
    "/triage-recommendation",
    response_model=ApiResponse[TriageRecommendationResponse],
    status_code=status.HTTP_200_OK
)
def get_triage_recommendation(
    request: TriageRecommendationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Part 1: Smart Priority Calculator & Part 2: Smart Developer Matcher.
    Sends bug title/description -> Returns priority score & recommended developers.
    """
    # 1. Calculate Priority Score
    priority_result = triage_service.calculate_priority_score(
        severity=request.severity or "MEDIUM",
        category=request.category or "General"
    )

    # 2. Recommend Developers
    dev_matches = triage_service.recommend_developers(
        db=db,
        title=request.title,
        description=request.description or "",
        limit=3
    )

    dev_recommendations = [
        DeveloperRecommendation(**d)
        for d in dev_matches
    ]

    response_data = TriageRecommendationResponse(
        priority_score=priority_result["priority_score"],
        recommended_priority=priority_result["recommended_priority"],
        severity=priority_result["severity"],
        severity_weight=priority_result["severity_weight"],
        category=priority_result["category"],
        category_urgency_weight=priority_result["category_urgency_weight"],
        formula=priority_result["formula"],
        recommended_developers=dev_recommendations
    )

    return ApiResponse(
        success=True,
        message="Triage recommendation generated successfully",
        data=response_data
    )
