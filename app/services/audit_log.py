from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.audit_log import AuditLog
from app.models.user import User

def log_action(
    db: Session, 
    issue_id: int, 
    action: str, 
    performed_by: Optional[User], 
    old_value: Optional[str] = None, 
    new_value: Optional[str] = None
) -> AuditLog:
    log = AuditLog(
        issue_id=issue_id,
        action=action,
        performed_by_id=performed_by.id if performed_by else None,
        old_value=old_value,
        new_value=new_value
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def get_issue_logs(db: Session, issue_id: int) -> List[AuditLog]:
    return db.query(AuditLog).filter(AuditLog.issue_id == issue_id).order_by(AuditLog.timestamp.desc()).all()

def get_recent_logs(db: Session, limit: int = 50) -> List[AuditLog]:
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
