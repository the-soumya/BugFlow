from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.schemas.user import UserMinResponse

class AuditLogResponse(BaseModel):
    id: int
    issue_id: int
    action: str
    performed_by_id: Optional[int]
    timestamp: datetime
    old_value: Optional[str]
    new_value: Optional[str]
    performed_by: Optional[UserMinResponse] = None

    class Config:
        from_attributes = True
