from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from datetime import datetime
from typing import List, Optional, Tuple, Dict
from app.models.issue import Issue, IssueType, WorkflowState, IssuePriority, IssueSeverity
from app.models.project import Project
from app.models.user import User
from app.schemas.issue import IssueCreateRequest, IssueUpdateRequest, StatusUpdateRequest
from app.services.project import get_project
from app.services.audit_log import log_action
from app.exceptions import ResourceNotFound, InvalidTransition

def create_issue(db: Session, project_id: int, request: IssueCreateRequest, reporter: User) -> Issue:
    # Verify project exists
    project = get_project(db, project_id)

    # Autogenerate unique issue key (e.g., BUG-1, BUG-2)
    count = db.query(Issue).filter(Issue.project_id == project_id).count()
    while True:
        count += 1
        key = f"{project.project_key}-{count}"
        existing = db.query(Issue).filter(Issue.issue_key == key).first()
        if not existing:
            break

    issue = Issue(
        issue_key=key,
        title=request.title,
        description=request.description,
        issue_type=request.issue_type,
        status=WorkflowState.OPEN,
        priority=request.priority,
        severity=request.severity,
        project_id=project_id,
        reporter_id=reporter.id,
        assignee_id=None
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)

    # Log audit event
    log_action(
        db=db,
        issue_id=issue.id,
        action="ISSUE_CREATED",
        performed_by=reporter,
        old_value=None,
        new_value=f"Created issue {key} with title '{request.title}'"
    )

    return issue

def get_issue(db: Session, issue_id: int) -> Issue:
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise ResourceNotFound(f"Issue with ID {issue_id} not found")
    return issue

def get_project_issues(
    db: Session,
    project_id: int,
    status: Optional[WorkflowState] = None,
    priority: Optional[IssuePriority] = None,
    severity: Optional[IssueSeverity] = None,
    assignee_id: Optional[int] = None,
    issue_type: Optional[IssueType] = None,
    page: int = 0,
    size: int = 10
) -> Tuple[List[Issue], int]:
    # Verify project exists
    get_project(db, project_id)

    query = db.query(Issue).filter(Issue.project_id == project_id)

    # Apply filters
    if status:
        query = query.filter(Issue.status == status)
    if priority:
        query = query.filter(Issue.priority == priority)
    if severity:
        query = query.filter(Issue.severity == severity)
    if assignee_id:
        query = query.filter(Issue.assignee_id == assignee_id)
    if issue_type:
        query = query.filter(Issue.issue_type == issue_type)

    total_count = query.count()

    # Apply pagination
    offset = page * size
    issues = query.order_by(Issue.created_at.desc()).offset(offset).limit(size).all()

    return issues, total_count

def update_issue(db: Session, issue_id: int, request: IssueUpdateRequest, user: User) -> Issue:
    issue = get_issue(db, issue_id)
    
    changes = []
    
    # Track and apply changes
    if request.title is not None and request.title != issue.title:
        changes.append(("title", issue.title, request.title))
        issue.title = request.title
        
    if request.description is not None and request.description != issue.description:
        changes.append(("description", issue.description, request.description))
        issue.description = request.description
        
    if request.issue_type is not None and request.issue_type != issue.issue_type:
        changes.append(("issue_type", issue.issue_type.value, request.issue_type.value))
        issue.issue_type = request.issue_type
        
    if request.priority is not None and request.priority != issue.priority:
        changes.append(("priority", issue.priority.value, request.priority.value))
        issue.priority = request.priority
        
    if request.severity is not None and request.severity != issue.severity:
        changes.append(("severity", issue.severity.value, request.severity.value))
        issue.severity = request.severity

    if changes:
        db.commit()
        db.refresh(issue)
        # Log all changes in audit log
        for field, old_val, new_val in changes:
            log_action(
                db=db,
                issue_id=issue.id,
                action="ISSUE_UPDATED",
                performed_by=user,
                old_value=f"{field}: {old_val}",
                new_value=f"{field}: {new_val}"
            )
            
    return issue

def assign_issue(db: Session, issue_id: int, assignee_id: Optional[int], user: User) -> Issue:
    issue = get_issue(db, issue_id)
    
    old_assignee_name = issue.assignee.name if issue.assignee else "Unassigned"
    
    new_assignee = None
    if assignee_id is not None:
        new_assignee = db.query(User).filter(User.id == assignee_id).first()
        if not new_assignee:
            raise ResourceNotFound(f"Assignee user with ID {assignee_id} not found")
        issue.assignee_id = assignee_id
        new_assignee_name = new_assignee.name
    else:
        issue.assignee_id = None
        new_assignee_name = "Unassigned"

    if old_assignee_name != new_assignee_name:
        db.commit()
        db.refresh(issue)
        log_action(
            db=db,
            issue_id=issue.id,
            action="ISSUE_ASSIGNED",
            performed_by=user,
            old_value=old_assignee_name,
            new_value=new_assignee_name
        )
        
    return issue

def update_issue_status(db: Session, issue_id: int, request: StatusUpdateRequest, user: User) -> Issue:
    issue = get_issue(db, issue_id)
    old_status = issue.status
    new_status = request.status
    
    if old_status == new_status:
        return issue

    # Validate state machine transitions
    valid_transitions = {
        WorkflowState.OPEN: [WorkflowState.IN_PROGRESS],
        WorkflowState.IN_PROGRESS: [WorkflowState.RESOLVED],
        WorkflowState.RESOLVED: [WorkflowState.CLOSED, WorkflowState.REOPENED],
        WorkflowState.CLOSED: [],
        WorkflowState.REOPENED: [WorkflowState.IN_PROGRESS]
    }
    
    allowed = valid_transitions.get(old_status, [])
    
    # We allow the transition if it is in the list, or if the user is ADMIN/PROJECT_MANAGER (as an override safety)
    # Wait, the prompt says "Prevent obviously invalid transitions." 
    # Let's enforce the transition rules strictly for all users unless we want general override. The prompt is:
    # "Allow basic transitions such as: OPEN -> IN_PROGRESS, IN_PROGRESS -> RESOLVED, etc. Prevent obviously invalid transitions."
    # So we strictly enforce it.
    if new_status not in allowed:
        raise InvalidTransition(f"Cannot transition status from {old_status.value} to {new_status.value}")
        
    issue.status = new_status
    
    # Set resolved_at timestamp on entering resolved or closed states
    if new_status in [WorkflowState.RESOLVED, WorkflowState.CLOSED]:
        issue.resolved_at = datetime.utcnow()
    else:
        issue.resolved_at = None
        
    db.commit()
    db.refresh(issue)
    
    # Log audit event
    log_action(
        db=db,
        issue_id=issue.id,
        action="STATUS_CHANGED",
        performed_by=user,
        old_value=old_status.value,
        new_value=new_status.value
    )
    
    return issue

def get_issue_summary(db: Session, project_id: int) -> Dict:
    # Verify project exists
    get_project(db, project_id)
    
    issues = db.query(Issue).filter(Issue.project_id == project_id).all()
    
    # Initialize metrics
    total_issues = len(issues)
    open_issues = sum(1 for i in issues if i.status == WorkflowState.OPEN)
    in_progress = sum(1 for i in issues if i.status == WorkflowState.IN_PROGRESS)
    resolved = sum(1 for i in issues if i.status == WorkflowState.RESOLVED)
    closed = sum(1 for i in issues if i.status == WorkflowState.CLOSED)
    
    critical = sum(1 for i in issues if i.priority == IssuePriority.CRITICAL or i.severity == IssueSeverity.CRITICAL)
    high_priority = sum(1 for i in issues if i.priority == IssuePriority.HIGH)
    
    # Formulate grouped counts
    status_counts = {}
    priority_counts = {}
    severity_counts = {}
    type_counts = {}
    
    for s in WorkflowState:
        status_counts[s.value] = 0
    for p in IssuePriority:
        priority_counts[p.value] = 0
    for sv in IssueSeverity:
        severity_counts[sv.value] = 0
    for t in IssueType:
        type_counts[t.value] = 0
        
    for i in issues:
        status_counts[i.status.value] = status_counts.get(i.status.value, 0) + 1
        priority_counts[i.priority.value] = priority_counts.get(i.priority.value, 0) + 1
        severity_counts[i.severity.value] = severity_counts.get(i.severity.value, 0) + 1
        type_counts[i.issue_type.value] = type_counts.get(i.issue_type.value, 0) + 1
        
    return {
        "totalIssues": total_issues,
        "openIssues": open_issues,
        "inProgressIssues": in_progress,
        "resolvedIssues": resolved,
        "closedIssues": closed,
        "criticalIssues": critical,
        "highPriorityIssues": high_priority,
        "statusCounts": status_counts,
        "priorityCounts": priority_counts,
        "severityCounts": severity_counts,
        "typeCounts": type_counts
    }
