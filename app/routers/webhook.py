from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import re
from datetime import datetime

from app.database import get_db
from app.models.issue import Issue, WorkflowState
from app.services.audit_log import log_action
from app.schemas import ApiResponse

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])

class GitWebhookPayload(BaseModel):
    commit_message: Optional[str] = Field(None, description="Commit message containing issue reference like 'fixes #2'")
    message: Optional[str] = Field(None, description="Alternative field for commit message")
    commit_hash: Optional[str] = Field("a7f8c92", description="Git commit hash / SHA")
    commit_id: Optional[str] = Field(None, description="Alternative field for commit hash")
    author: Optional[str] = Field("CI/CD Bot", description="Author of the commit")
    branch: Optional[str] = Field("main", description="Git branch")
    repository: Optional[str] = Field("BugFlow", description="Repository name")
    commits: Optional[List[Dict[str, Any]]] = Field(None, description="GitHub style commits list")
    head_commit: Optional[Dict[str, Any]] = None

class GitWebhookResponse(BaseModel):
    matched_issues: List[int]
    updated_issues: List[Dict[str, Any]]
    commit_hash: str
    message: str

@router.post("/git", response_model=ApiResponse[GitWebhookResponse])
def git_webhook(
    payload: GitWebhookPayload,
    db: Session = Depends(get_db)
):
    # Extract commit message from various formats (raw text, GitHub webhook format, etc.)
    text = payload.commit_message or payload.message or ""
    if not text and payload.head_commit:
        text = payload.head_commit.get("message", "")
    if not text and payload.commits:
        text = " ".join(c.get("message", "") for c in payload.commits)

    # Extract commit hash
    commit_sha = payload.commit_hash or payload.commit_id or "a7f8c92"
    if payload.head_commit and "id" in payload.head_commit:
        commit_sha = payload.head_commit["id"][:7]

    if not text:
        return ApiResponse(
            success=False,
            message="No commit message provided in payload",
            data=GitWebhookResponse(
                matched_issues=[],
                updated_issues=[],
                commit_hash=commit_sha,
                message="No commit message found"
            )
        )

    # Search for keywords like fixes #2, closes #5, resolves #8, fixes BUG-2, etc.
    # Pattern matches: (fixes|closes|resolves|fixed|closed|resolved|fix|close|resolve)\s*(?:#|BUG-)?(\d+)
    pattern = re.compile(r"(?:fixes|closes|resolves|fixed|closed|resolved|fix|close|resolve)\s+(?:#|BUG-)?(\d+)", re.IGNORECASE)
    matches = pattern.findall(text)

    # Also capture direct references like #\d+ if keywords are present in text
    if not matches and any(kw in text.lower() for kw in ["fix", "close", "resolve"]):
        matches = re.findall(r"#(\d+)", text)

    # Convert to unique integer IDs
    issue_ids = []
    for m in matches:
        try:
            val = int(m)
            if val not in issue_ids:
                issue_ids.append(val)
        except ValueError:
            continue

    updated = []
    for issue_id in issue_ids:
        # Search by id or issue_key
        issue = db.query(Issue).filter(
            (Issue.id == issue_id) | (Issue.issue_key == f"BUG-{issue_id}")
        ).first()

        if issue:
            old_status = issue.status
            # Auto-transition status to QA_VERIFICATION
            issue.status = WorkflowState.QA_VERIFICATION
            issue.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(issue)

            # Record audit log entry: "Auto-transitioned by Git commit #<commit_hash>"
            audit_message = f"Auto-transitioned by Git commit #{commit_sha}"
            log_action(
                db=db,
                issue_id=issue.id,
                action=audit_message,
                performed_by=None,
                old_value=old_status.value if hasattr(old_status, 'value') else str(old_status),
                new_value=f"{WorkflowState.QA_VERIFICATION.value} ({audit_message})"
            )

            updated.append({
                "id": issue.id,
                "issue_key": issue.issue_key,
                "title": issue.title,
                "old_status": old_status.value if hasattr(old_status, 'value') else str(old_status),
                "new_status": issue.status.value,
                "audit_entry": audit_message
            })

    result_message = f"Processed Git commit #{commit_sha}. Successfully transitioned {len(updated)} issue(s) to QA_VERIFICATION."
    return ApiResponse(
        success=True,
        message=result_message,
        data=GitWebhookResponse(
            matched_issues=issue_ids,
            updated_issues=updated,
            commit_hash=commit_sha,
            message=text
        )
    )
