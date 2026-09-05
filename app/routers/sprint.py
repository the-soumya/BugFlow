from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.sprint import (
    SprintCreateRequest,
    SprintStatusUpdateRequest,
    SprintResponse,
    SprintSummaryResponse
)
from app.schemas.issue import IssueResponse
from app.schemas.response import ApiResponse
from app.services import sprint as sprint_service
from app.security import get_current_user, RoleChecker
from app.models.user import User, UserRole

router = APIRouter(
    prefix="/api/v1/sprints",
    tags=["Agile Sprints & Backlog"]
)

@router.post(
    "/",
    response_model=ApiResponse[SprintResponse],
    status_code=status.HTTP_201_CREATED
)
def create_sprint(
    request: SprintCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        RoleChecker([UserRole.ADMIN, UserRole.PROJECT_MANAGER])
    )
):
    """
    Creates a new Sprint container (name, goal, start_date, end_date).
    """
    sprint = sprint_service.create_sprint(db=db, request=request)
    
    # Format with initial metrics
    resp = SprintResponse(
        id=sprint.id,
        project_id=sprint.project_id,
        name=sprint.name,
        goal=sprint.goal,
        start_date=sprint.start_date,
        end_date=sprint.end_date,
        status=sprint.status,
        velocity=sprint.velocity,
        created_at=sprint.created_at,
        updated_at=sprint.updated_at,
        total_issues=0,
        resolved_issues=0,
        progress_percentage=0.0
    )

    return ApiResponse(
        success=True,
        message="Sprint created successfully",
        data=resp
    )


@router.get(
    "/",
    response_model=ApiResponse[List[SprintResponse]],
    status_code=status.HTTP_200_OK
)
def list_sprints(
    projectId: Optional[int] = Query(None),
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists all active and past Sprints with completion progress and velocity.
    """
    target_id = projectId if projectId is not None else project_id
    sprints = sprint_service.list_sprints(db=db, project_id=target_id)

    response_data = [
        SprintResponse(**s)
        for s in sprints
    ]

    return ApiResponse(
        success=True,
        message="Sprints retrieved successfully",
        data=response_data
    )


@router.post(
    "/{id}/add-issue/{issue_id}",
    response_model=ApiResponse[IssueResponse],
    status_code=status.HTTP_200_OK
)
def add_issue_to_sprint(
    id: int,
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Moves a bug from backlog into the Sprint.
    """
    issue = sprint_service.add_issue_to_sprint(
        db=db,
        sprint_id=id,
        issue_id=issue_id,
        user=current_user
    )

    return ApiResponse(
        success=True,
        message="Issue moved into sprint successfully",
        data=IssueResponse.model_validate(issue)
    )


@router.delete(
    "/{id}/issues/{issue_id}",
    response_model=ApiResponse[IssueResponse],
    status_code=status.HTTP_200_OK
)
def remove_issue_from_sprint(
    id: int,
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Removes an issue from a sprint back to the product backlog.
    """
    issue = sprint_service.remove_issue_from_sprint(
        db=db,
        sprint_id=id,
        issue_id=issue_id,
        user=current_user
    )

    return ApiResponse(
        success=True,
        message="Issue moved back to backlog",
        data=IssueResponse.model_validate(issue)
    )


@router.get(
    "/backlog",
    response_model=ApiResponse[List[IssueResponse]],
    status_code=status.HTTP_200_OK
)
def get_backlog_issues(
    projectId: Optional[int] = Query(None),
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetches the Product Backlog: all unassigned bugs not currently in any sprint.
    """
    target_id = projectId if projectId is not None else project_id
    issues = sprint_service.get_backlog_issues(db=db, project_id=target_id)

    return ApiResponse(
        success=True,
        message="Backlog issues retrieved successfully",
        data=[IssueResponse.model_validate(i) for i in issues]
    )


@router.put(
    "/{id}/status",
    response_model=ApiResponse[SprintResponse],
    status_code=status.HTTP_200_OK
)
def update_sprint_status(
    id: int,
    request: SprintStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        RoleChecker([UserRole.ADMIN, UserRole.PROJECT_MANAGER])
    )
):
    """
    Updates sprint status (PLANNING, ACTIVE, COMPLETED).
    When marked COMPLETED, calculates and records team velocity.
    """
    sprint = sprint_service.update_sprint_status(
        db=db,
        sprint_id=id,
        new_status=request.status,
        user=current_user
    )

    sprints = sprint_service.list_sprints(db=db)
    matching = next((s for s in sprints if s["id"] == sprint.id), None)
    
    if matching:
        resp = SprintResponse(**matching)
    else:
        resp = SprintResponse.model_validate(sprint)

    return ApiResponse(
        success=True,
        message=f"Sprint status updated to {sprint.status.value}. Velocity: {sprint.velocity}",
        data=resp
    )
