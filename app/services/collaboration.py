import os
import shutil
import uuid
from typing import List
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.collaboration import Comment, Attachment
from app.models.user import User
from app.models.issue import Issue
from app.services.audit_log import log_action
from app.exceptions import ResourceNotFound, BadRequest

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".log", ".txt", ".pdf"}

def add_comment(db: Session, issue_id: int, user: User, content: str) -> Comment:
    # Verify issue exists
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise ResourceNotFound(f"Issue with ID {issue_id} not found")
        
    cleaned_content = (content or "").strip()
    if not cleaned_content:
        raise BadRequest("Comment content cannot be empty")
        
    comment = Comment(
        issue_id=issue_id,
        user_id=user.id,
        content=cleaned_content
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    # Audit log entry
    preview = cleaned_content[:40] + "..." if len(cleaned_content) > 40 else cleaned_content
    log_action(
        db=db,
        issue_id=issue_id,
        action="COMMENT_ADDED",
        performed_by=user,
        old_value=None,
        new_value=f"{user.name} commented: '{preview}'"
    )
    
    return comment

def get_comments(db: Session, issue_id: int) -> List[Comment]:
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise ResourceNotFound(f"Issue with ID {issue_id} not found")
        
    return (
        db.query(Comment)
        .filter(Comment.issue_id == issue_id)
        .order_by(Comment.created_at.asc())
        .all()
    )

def save_attachment(db: Session, issue_id: int, user: User, upload_file: UploadFile) -> Attachment:
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise ResourceNotFound(f"Issue with ID {issue_id} not found")
        
    orig_filename = upload_file.filename or "attachment.dat"
    ext = os.path.splitext(orig_filename)[1].lower()
    
    if ext not in ALLOWED_EXTENSIONS:
        raise BadRequest(f"File type '{ext}' not allowed. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    # Generate unique stored filename
    safe_stored_name = f"{uuid.uuid4().hex}_{orig_filename}"
    dest_path = os.path.join(UPLOAD_DIR, safe_stored_name)

    # Save to disk
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
        
    file_size = os.path.getsize(dest_path)
    relative_path = f"/uploads/{safe_stored_name}"

    attachment = Attachment(
        issue_id=issue_id,
        user_id=user.id,
        filename=orig_filename,
        file_path=relative_path,
        file_type=upload_file.content_type or ext,
        file_size=file_size
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    # Audit log entry
    log_action(
        db=db,
        issue_id=issue_id,
        action="ATTACHMENT_UPLOADED",
        performed_by=user,
        old_value=None,
        new_value=f"Uploaded file '{orig_filename}' ({round(file_size/1024, 1)} KB)"
    )

    return attachment

def get_attachments(db: Session, issue_id: int) -> List[Attachment]:
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise ResourceNotFound(f"Issue with ID {issue_id} not found")

    return (
        db.query(Attachment)
        .filter(Attachment.issue_id == issue_id)
        .order_by(Attachment.uploaded_at.asc())
        .all()
    )

def get_attachment_by_id(db: Session, attachment_id: int) -> Attachment:
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise ResourceNotFound(f"Attachment with ID {attachment_id} not found")
    return attachment
