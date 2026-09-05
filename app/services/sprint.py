from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.sprint import Sprint, SprintStatus
from app.models.issue import Issue, WorkflowState
from app.models.project import Project
from app.models.user import User
from app.schemas.sprint import SprintCreateRequest
from app.services.audit_log import log_action
from app.exceptions import ResourceNotFound, BadRequest

def create_sprint(db: Session, request: SprintCreateRequest) -> Sprint:
    # If project_id provided, verify exists
    proj_id = request.project_id
    if proj_id is None:
        first_proj = db.query(Project).first()
        proj_id = first_proj.id if first_proj else None
    else:
        proj = db.query(Project).filter(Project.id == proj_id).first()
        if not proj:
            raise ResourceNotFound(f"Project with ID {proj_id} not found")

    start_date = request.start_date or datetime.utcnow()
    end_date = request.end_date or (start_date + timedelta(days=14))

    sprint = Sprint(
        project_id=proj_id,
        name=request.name,
        goal=request.goal,
        start_date=start_date,
        end_date=end_date,
        status=SprintStatus.ACTIVE,
        velocity=0
    )
    db.add(sprint)
    db.commit()
    db.refresh(sprint)
    return sprint

def get_sprint_by_id(db: Session, sprint_id: int) -> Sprint:
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise ResourceNotFound(f"Sprint with ID {sprint_id} not found")
    return sprint

def list_sprints(db: Session, project_id: Optional[int] = None) -> List[Dict[str, Any]]:
    query = db.query(Sprint)
    if project_id is not None:
        query = query.filter(Sprint.project_id == project_id)
        
    sprints = query.order_by(Sprint.created_at.desc()).all()
    
    result = []
    for s in sprints:
        issues = db.query(Issue).filter(Issue.sprint_id == s.id).all()
        total_issues = len(issues)
        resolved_issues = sum(1 for i in issues if i.status in [WorkflowState.RESOLVED, WorkflowState.CLOSED])
        progress_pct = round((resolved_issues / total_issues * 100), 1) if total_issues > 0 else 0.0

        result.append({
            "id": s.id,
            "project_id": s.project_id,
            "name": s.name,
            "goal": s.goal,
            "start_date": s.start_date,
            "end_date": s.end_date,
            "status": s.status,
            "velocity": s.velocity,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
            "total_issues": total_issues,
            "resolved_issues": resolved_issues,
            "progress_percentage": progress_pct
        })
    return result

def add_issue_to_sprint(db: Session, sprint_id: int, issue_id: int, user: User) -> Issue:
    sprint = get_sprint_by_id(db, sprint_id)
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise ResourceNotFound(f"Issue with ID {issue_id} not found")

    old_sprint_name = issue.sprint.name if issue.sprint else "Product Backlog"
    issue.sprint_id = sprint.id
    db.commit()
    db.refresh(issue)

    # Record audit log entry
    log_action(
        db=db,
        issue_id=issue.id,
        action="SPRINT_ASSIGNED",
        performed_by=user,
        old_value=old_sprint_name,
        new_value=sprint.name
    )

    return issue

def remove_issue_from_sprint(db: Session, sprint_id: int, issue_id: int, user: User) -> Issue:
    sprint = get_sprint_by_id(db, sprint_id)
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise ResourceNotFound(f"Issue with ID {issue_id} not found")

    if issue.sprint_id == sprint.id:
        issue.sprint_id = None
        db.commit()
        db.refresh(issue)

        log_action(
            db=db,
            issue_id=issue.id,
            action="SPRINT_REMOVED",
            performed_by=user,
            old_value=sprint.name,
            new_value="Product Backlog"
        )

    return issue

def get_backlog_issues(db: Session, project_id: Optional[int] = None) -> List[Issue]:
    query = db.query(Issue).filter(Issue.sprint_id == None)
    if project_id is not None:
        query = query.filter(Issue.project_id == project_id)
    return query.order_by(Issue.created_at.desc()).all()

def update_sprint_status(db: Session, sprint_id: int, new_status: SprintStatus, user: User) -> Sprint:
    sprint = get_sprint_by_id(db, sprint_id)
    old_status = sprint.status
    sprint.status = new_status
    
    # Velocity calculation upon COMPLETED:
    # How many bugs the team successfully resolved in this sprint
    if new_status == SprintStatus.COMPLETED:
        resolved_count = db.query(Issue).filter(
            Issue.sprint_id == sprint.id,
            Issue.status.in_([WorkflowState.RESOLVED, WorkflowState.CLOSED])
        ).count()
        sprint.velocity = resolved_count
        
    sprint.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sprint)
    return sprint
