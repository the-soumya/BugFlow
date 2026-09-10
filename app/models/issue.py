import enum
from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class IssueType(str, enum.Enum):
    BUG = "BUG"
    FEATURE = "FEATURE"
    ENHANCEMENT = "ENHANCEMENT"
    TASK = "TASK"

class WorkflowState(str, enum.Enum):
    REPORTED = "REPORTED"
    TRIAGED = "TRIAGED"
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    QA_VERIFICATION = "QA_VERIFICATION"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    REOPENED = "REOPENED"

class IssuePriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    URGENT = "URGENT"

class IssueSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    TRIVIAL = "TRIVIAL"

class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    issue_key = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(String(2000), nullable=True)
    issue_type = Column(Enum(IssueType), default=IssueType.BUG, nullable=False)
    status = Column(Enum(WorkflowState), default=WorkflowState.REPORTED, nullable=False)
    priority = Column(Enum(IssuePriority), default=IssuePriority.MEDIUM, nullable=False)
    severity = Column(Enum(IssueSeverity), default=IssueSeverity.MEDIUM, nullable=False)
    category = Column(String(100), default="General", nullable=True)
    priority_score = Column(Float, nullable=True)
    
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sprint_id = Column(Integer, ForeignKey("sprints.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    project = relationship("Project")
    reporter = relationship("User", foreign_keys=[reporter_id])
    assignee = relationship("User", foreign_keys=[assignee_id])
    sprint = relationship("Sprint", back_populates="issues")
    comments = relationship("Comment", back_populates="issue", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="issue", cascade="all, delete-orphan")

    @property
    def resolution_time_hours(self):
        if self.status in [WorkflowState.RESOLVED, WorkflowState.CLOSED]:
            res_time = self.resolved_at or self.updated_at
            if res_time and self.created_at:
                c_at = self.created_at
                r_at = res_time
                if c_at.tzinfo is None and r_at.tzinfo is not None:
                    c_at = c_at.replace(tzinfo=r_at.tzinfo)
                elif r_at.tzinfo is None and c_at.tzinfo is not None:
                    r_at = r_at.replace(tzinfo=c_at.tzinfo)
                diff = (r_at - c_at).total_seconds() / 3600.0
                # If negative due to UTC vs IST (+5.5h) offset, adjust
                if diff < 0:
                    if diff + 5.5 >= 0:
                        diff = diff + 5.5
                    else:
                        diff = abs(diff)
                return round(max(0.0, diff), 2)
        return None

    @property
    def resolution_time_formatted(self):
        hrs = self.resolution_time_hours
        if hrs is not None:
            if hrs >= 24.0:
                days = round(hrs / 24.0, 1)
                return f"{days} days ({round(hrs, 1)} hrs)"
            return f"{round(hrs, 1)} hrs"
        return None

