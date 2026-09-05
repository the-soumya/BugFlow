import os
from typing import List
from fastapi import APIRouter, Depends, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.collaboration import (
    CommentCreateRequest,
    CommentResponse,
    AttachmentResponse
)
from app.schemas.audit_log import AuditLogResponse
from app.schemas.response import ApiResponse
from app.services import collaboration as collab_service
from app.services import audit_log as audit_service
from app.security import get_current_user
from app.models.user import User

router = APIRouter(
    prefix="/api/v1/collaboration",
    tags=["Collaboration & Attachments"]
)

# =========================================================================
# COMMENTS
# =========================================================================

@router.post(
    "/issues/{id}/comments",
    response_model=ApiResponse[CommentResponse],
    status_code=status.HTTP_201_CREATED
)
def create_comment(
    id: int,
    request: CommentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Posts a new message/comment on a bug ticket.
    """
    comment = collab_service.add_comment(
        db=db,
        issue_id=id,
        user=current_user,
        content=request.content
    )

    return ApiResponse(
        success=True,
        message="Comment posted successfully",
        data=CommentResponse.model_validate(comment)
    )


@router.get(
    "/issues/{id}/comments",
    response_model=ApiResponse[List[CommentResponse]],
    status_code=status.HTTP_200_OK
)
def get_comments(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetches the full chat history for a bug ticket.
    """
    comments = collab_service.get_comments(db=db, issue_id=id)

    return ApiResponse(
        success=True,
        message="Comments retrieved successfully",
        data=[CommentResponse.model_validate(c) for c in comments]
    )


# =========================================================================
# ATTACHMENTS
# =========================================================================

@router.post(
    "/issues/{id}/attachments",
    response_model=ApiResponse[AttachmentResponse],
    status_code=status.HTTP_201_CREATED
)
def upload_attachment(
    id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a screenshot/error log file for a bug (.png, .jpg, .log).
    """
    attachment = collab_service.save_attachment(
        db=db,
        issue_id=id,
        user=current_user,
        upload_file=file
    )

    return ApiResponse(
        success=True,
        message="Attachment uploaded successfully",
        data=AttachmentResponse.model_validate(attachment)
    )


@router.get(
    "/issues/{id}/attachments",
    response_model=ApiResponse[List[AttachmentResponse]],
    status_code=status.HTTP_200_OK
)
def list_attachments(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists all attachments for an issue.
    """
    attachments = collab_service.get_attachments(db=db, issue_id=id)

    return ApiResponse(
        success=True,
        message="Attachments retrieved successfully",
        data=[AttachmentResponse.model_validate(a) for a in attachments]
    )


@router.get(
    "/attachments/{attachment_id}/download"
)
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Downloads or serves an attachment file.
    """
    attachment = collab_service.get_attachment_by_id(db=db, attachment_id=attachment_id)
    
    # Resolve physical disk path
    upload_dir = collab_service.UPLOAD_DIR
    filename_on_disk = os.path.basename(attachment.file_path)
    file_disk_path = os.path.join(upload_dir, filename_on_disk)

    if not os.path.exists(file_disk_path):
        from app.exceptions import ResourceNotFound
        raise ResourceNotFound("Attachment file not found on server")

    return FileResponse(
        path=file_disk_path,
        filename=attachment.filename,
        media_type=attachment.file_type or "application/octet-stream"
    )


# =========================================================================
# LIVE ACTIVITY STREAM
# =========================================================================

@router.get(
    "/activity-stream",
    response_model=ApiResponse[List[AuditLogResponse]],
    status_code=status.HTTP_200_OK
)
def get_activity_stream(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns the recent real-time activity stream across all issues.
    """
    logs = audit_service.get_recent_logs(db=db, limit=limit)
    return ApiResponse(
        success=True,
        message="Activity stream retrieved successfully",
        data=[AuditLogResponse.model_validate(l) for l in logs]
    )

