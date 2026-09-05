from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.schemas import (
    IssueCreateRequest,
    IssueUpdateRequest,
    AssignIssueRequest,
    StatusUpdateRequest,
    IssueResponse,
    IssueSummaryResponse,
    AuditLogResponse,
    ApiResponse
)
from app.services import issue as issue_service
from app.services import audit_log as audit_service
from app.security import get_current_user, RoleChecker
from app.models.user import User, UserRole
from app.models.issue import IssueType, WorkflowState, IssuePriority, IssueSeverity

router = APIRouter(tags=["Issues"])


@router.post(
    "/api/projects/{projectId}/issues",
    response_model=ApiResponse[IssueResponse],
    status_code=status.HTTP_201_CREATED
)
def create_issue(
    projectId: int,
    request: IssueCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    issue = issue_service.create_issue(db, projectId, request, current_user)

    return ApiResponse(
        success=True,
        message="Issue created successfully",
        data=IssueResponse.model_validate(issue)
    )


@router.get(
    "/api/projects/{projectId}/issues",
    response_model=ApiResponse[dict]
)
def get_project_issues(
    projectId: int,
    status: Optional[WorkflowState] = None,
    priority: Optional[IssuePriority] = None,
    severity: Optional[IssueSeverity] = None,
    assignee: Optional[int] = Query(None, alias="assignee"),
    reporter: Optional[int] = Query(None, alias="reporter"),
    issueType: Optional[IssueType] = Query(None, alias="issueType"),
    page: int = Query(0, ge=0),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    issues, total = issue_service.get_project_issues(
        db,
        projectId,
        status,
        priority,
        severity,
        assignee,
        issueType,
        reporter,
        page,
        size
    )

    response_data = [
        IssueResponse.model_validate(i)
        for i in issues
    ]

    total_pages = (total + size - 1) // size if total > 0 else 0

    return ApiResponse(
        success=True,
        message="Issues retrieved successfully",
        data={
            "content": response_data,
            "totalElements": total,
            "totalPages": total_pages,
            "pageNumber": page,
            "pageSize": size
        }
    )


@router.get(
    "/api/issues",
    response_model=ApiResponse[dict]
)
def list_all_issues(
    projectId: Optional[int] = Query(None),
    project_id: Optional[int] = Query(None),
    status: Optional[WorkflowState] = None,
    priority: Optional[IssuePriority] = None,
    severity: Optional[IssueSeverity] = None,
    assignee: Optional[int] = Query(None, alias="assignee"),
    reporter: Optional[int] = Query(None, alias="reporter"),
    issueType: Optional[IssueType] = Query(None, alias="issueType"),
    page: int = Query(0, ge=0),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    target_project_id = projectId if projectId is not None else project_id
    if target_project_id is not None:
        issues, total = issue_service.get_project_issues(
            db, target_project_id, status, priority, severity, assignee, issueType, reporter, page, size
        )
    else:
        from app.models.issue import Issue
        query = db.query(Issue)
        if status:
            query = query.filter(Issue.status == status)
        if priority:
            query = query.filter(Issue.priority == priority)
        if severity:
            query = query.filter(Issue.severity == severity)
        if assignee:
            query = query.filter(Issue.assignee_id == assignee)
        if reporter:
            query = query.filter(Issue.reporter_id == reporter)
        if issueType:
            query = query.filter(Issue.issue_type == issueType)
        total = query.count()
        issues = query.order_by(Issue.created_at.desc()).offset(page * size).limit(size).all()

    response_data = [
        IssueResponse.model_validate(i)
        for i in issues
    ]

    total_pages = (total + size - 1) // size if total > 0 else 0

    return ApiResponse(
        success=True,
        message="Issues retrieved successfully",
        data={
            "content": response_data,
            "totalElements": total,
            "totalPages": total_pages,
            "pageNumber": page,
            "pageSize": size
        }
    )


@router.get(
    "/api/issues/{id}",
    response_model=ApiResponse[IssueResponse]
)
def get_issue_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    issue = issue_service.get_issue(db, id)

    return ApiResponse(
        success=True,
        message="Issue retrieved successfully",
        data=IssueResponse.model_validate(issue)
    )


@router.put(
    "/api/issues/{id}",
    response_model=ApiResponse[IssueResponse]
)
def update_issue(
    id: int,
    request: IssueUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Custom authorization rules
    issue = issue_service.get_issue(db, id)

    if current_user.role not in [
        UserRole.ADMIN,
        UserRole.PROJECT_MANAGER
    ]:
        if (
            current_user.role == UserRole.DEVELOPER
            and issue.assignee_id != current_user.id
        ):
            from app.exceptions import Forbidden
            raise Forbidden(
                "Developers can only edit issues assigned to them"
            )

        elif (
            current_user.role in [UserRole.USER, UserRole.TESTER]
            and issue.reporter_id != current_user.id
        ):
            from app.exceptions import Forbidden
            raise Forbidden(
                "Testers and users can only edit issues they reported"
            )

    updated_issue = issue_service.update_issue(
        db,
        id,
        request,
        current_user
    )

    return ApiResponse(
        success=True,
        message="Issue updated successfully",
        data=IssueResponse.model_validate(updated_issue)
    )


@router.delete(
    "/api/issues/{id}",
    response_model=ApiResponse[dict]
)
def delete_issue(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        RoleChecker([
            UserRole.ADMIN,
            UserRole.PROJECT_MANAGER
        ])
    )
):
    issue = issue_service.get_issue(db, id)

    db.delete(issue)
    db.commit()

    return ApiResponse(
        success=True,
        message="Issue deleted successfully",
        data={"deleted_id": id}
    )


@router.put(
    "/api/issues/{id}/assign",
    response_model=ApiResponse[IssueResponse]
)
def assign_issue(
    id: int,
    request: AssignIssueRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    issue = issue_service.get_issue(db, id)

    # RBAC rules for assigning:
    # ADMIN, PROJECT_MANAGER: can assign any issue
    # TESTER: can assign issues they reported
    # DEVELOPER: can self-assign or reassign issues assigned to them
    if current_user.role == UserRole.TESTER and issue.reporter_id != current_user.id:
        from app.exceptions import Forbidden
        raise Forbidden("Testers can only assign issues they reported")
    elif current_user.role == UserRole.DEVELOPER:
        if request.assignee_id is not None and request.assignee_id != current_user.id and issue.assignee_id != current_user.id:
            from app.exceptions import Forbidden
            raise Forbidden("Developers can only self-assign or reassign issues assigned to them")
    elif current_user.role == UserRole.USER:
        from app.exceptions import Forbidden
        raise Forbidden("Standard users do not have permission to assign issues")

    updated_issue = issue_service.assign_issue(
        db,
        id,
        request.assignee_id,
        current_user
    )

    return ApiResponse(
        success=True,
        message="Issue assigned successfully",
        data=IssueResponse.model_validate(updated_issue)
    )


@router.put(
    "/api/issues/{id}/status",
    response_model=ApiResponse[IssueResponse]
)
def update_issue_status(
    id: int,
    request: StatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    issue = issue_service.get_issue(db, id)

    if (
        current_user.role == UserRole.DEVELOPER
        and issue.assignee_id != current_user.id
    ):
        from app.exceptions import Forbidden
        raise Forbidden(
            "Developers can only update status of issues assigned to them"
        )

    elif (
        current_user.role in [UserRole.USER, UserRole.TESTER]
        and issue.reporter_id != current_user.id
    ):
        from app.exceptions import Forbidden
        raise Forbidden(
            "Testers and users can only update status of issues they reported"
        )

    updated_issue = issue_service.update_issue_status(
        db,
        id,
        request,
        current_user
    )

    return ApiResponse(
        success=True,
        message="Issue status updated successfully",
        data=IssueResponse.model_validate(updated_issue)
    )


@router.get(
    "/api/projects/{projectId}/issues/summary",
    response_model=ApiResponse[IssueSummaryResponse]
)
def get_project_issues_summary(
    projectId: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    summary = issue_service.get_issue_summary(db, projectId)

    return ApiResponse(
        success=True,
        message="Issue summary retrieved successfully",
        data=IssueSummaryResponse(**summary)
    )


@router.get(
    "/api/issues/{id}/audit",
    response_model=ApiResponse[List[AuditLogResponse]]
)
def get_issue_audit_log(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    issue_service.get_issue(db, id)

    logs = audit_service.get_issue_logs(db, id)

    response_data = [
        AuditLogResponse.model_validate(l)
        for l in logs
    ]

    return ApiResponse(
        success=True,
        message="Audit log retrieved successfully",
        data=response_data
    )