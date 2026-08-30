from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas import ProjectRequest, ProjectResponse, ApiResponse
from app.services import project as project_service
from app.security import get_current_user, RoleChecker
from app.models.user import User, UserRole

router = APIRouter(prefix="/api/projects", tags=["Projects"])

# Enforce ADMIN or PROJECT_MANAGER for mutating actions
admin_or_pm = RoleChecker([UserRole.ADMIN, UserRole.PROJECT_MANAGER])


@router.post(
    "",
    response_model=ApiResponse[ProjectResponse],
    status_code=status.HTTP_201_CREATED
)
def create_project(
    request: ProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_pm)
):
    project = project_service.create_project(db, request, current_user)

    return ApiResponse(
        success=True,
        message="Project created successfully",
        data=ProjectResponse.model_validate(project)
    )


@router.get("", response_model=ApiResponse[List[ProjectResponse]])
def get_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    projects = project_service.get_projects(db)

    response_data = [
        ProjectResponse.model_validate(p)
        for p in projects
    ]

    return ApiResponse(
        success=True,
        message="Projects retrieved successfully",
        data=response_data
    )


@router.get("/{id}", response_model=ApiResponse[ProjectResponse])
def get_project_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = project_service.get_project(db, id)

    return ApiResponse(
        success=True,
        message="Project retrieved successfully",
        data=ProjectResponse.model_validate(project)
    )


@router.put("/{id}", response_model=ApiResponse[ProjectResponse])
def update_project(
    id: int,
    request: ProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_pm)
):
    project = project_service.update_project(db, id, request)

    return ApiResponse(
        success=True,
        message="Project updated successfully",
        data=ProjectResponse.model_validate(project)
    )


@router.delete("/{id}", response_model=ApiResponse[ProjectResponse])
def delete_project(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_pm)
):
    project = project_service.delete_project(db, id)

    return ApiResponse(
        success=True,
        message="Project deactivated successfully",
        data=ProjectResponse.model_validate(project)
    )