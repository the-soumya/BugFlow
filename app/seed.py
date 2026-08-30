from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.issue import Issue, IssueType, WorkflowState, IssuePriority, IssueSeverity
from app.security import get_password_hash
from datetime import datetime

def seed_data():
    db = SessionLocal()
    try:
        # Check if users already seeded
        user_count = db.query(User).count()
        if user_count > 0:
            print("Database already contains data, skipping seed.")
            return

        print("Seeding database with default users, projects, and issues...")

        # 1. Create Default Users (password is hashed 'password123')
        hashed_pwd = get_password_hash("password123")
        
        admin_user = User(name="System Administrator", email="admin@bugflow.com", password=hashed_pwd, role=UserRole.ADMIN)
        pm_user = User(name="John Doe", email="pm@bugflow.com", password=hashed_pwd, role=UserRole.PROJECT_MANAGER)
        dev_user = User(name="Alex Rivera", email="dev@bugflow.com", password=hashed_pwd, role=UserRole.DEVELOPER)
        tester_user = User(name="Bruce Wayne", email="tester@bugflow.com", password=hashed_pwd, role=UserRole.TESTER)
        std_user = User(name="Taylor Kim", email="user@bugflow.com", password=hashed_pwd, role=UserRole.USER)
        
        db.add_all([admin_user, pm_user, dev_user, tester_user, std_user])
        db.commit()
        
        # Refresh to get IDs
        for u in [admin_user, pm_user, dev_user, tester_user, std_user]:
            db.refresh(u)

        # 2. Create Project
        proj = Project(
            name="Mobile Reporter App",
            description="BugFlow Native Client for field reporters, featuring crash reporting and offline sync.",
            project_key="BUG",
            created_by_id=admin_user.id
        )
        db.add(proj)
        db.commit()
        db.refresh(proj)

        # 3. Create Issues (matching mockup)
        i1 = Issue(
            issue_key="BUG-1",
            title="Minor UI Glitch on Dashboard sidebar",
            description="The sidebar overflows on 13 inch laptop displays.",
            issue_type=IssueType.BUG,
            status=WorkflowState.OPEN,
            priority=IssuePriority.LOW,
            severity=IssueSeverity.LOW,
            project_id=proj.id,
            reporter_id=std_user.id,
            assignee_id=dev_user.id
        )
        i2 = Issue(
            issue_key="BUG-2",
            title="Error on Login with Special Characters in Password",
            description="B-002: Login button does not respond if the password contains '#', '&', or '%'.",
            issue_type=IssueType.BUG,
            status=WorkflowState.IN_PROGRESS,
            priority=IssuePriority.HIGH,
            severity=IssueSeverity.CRITICAL,
            project_id=proj.id,
            reporter_id=pm_user.id,
            assignee_id=pm_user.id
        )
        i3 = Issue(
            issue_key="BUG-3",
            title="PostgreSQL connection pool exhaustion under 200 req/s load",
            description="Database connections hang when load testing is run using Locust.",
            issue_type=IssueType.BUG,
            status=WorkflowState.OPEN,
            priority=IssuePriority.HIGH,
            severity=IssueSeverity.HIGH,
            project_id=proj.id,
            reporter_id=tester_user.id,
            assignee_id=tester_user.id
        )
        i4 = Issue(
            issue_key="BUG-4",
            title="Validate JWT token revocation and expiry edge cases",
            description="Verify blacklisting works for expired tokens.",
            issue_type=IssueType.TASK,
            status=WorkflowState.RESOLVED,
            priority=IssuePriority.HIGH,
            severity=IssueSeverity.CRITICAL,
            project_id=proj.id,
            reporter_id=admin_user.id,
            assignee_id=pm_user.id,
            resolved_at=datetime.utcnow()
        )
        i5 = Issue(
            issue_key="BUG-5",
            title="Sidebar does not remember collapse state on refresh",
            description="User has to click collapse every time they reload.",
            issue_type=IssueType.ENHANCEMENT,
            status=WorkflowState.OPEN,
            priority=IssuePriority.MEDIUM,
            severity=IssueSeverity.LOW,
            project_id=proj.id,
            reporter_id=std_user.id,
            assignee_id=None
        )
        i6 = Issue(
            issue_key="BUG-6",
            title="ERROR OR LOGIN WITH SPECIAL CHARACRES",
            description="Auto-generated triage issue from crash reporter log.",
            issue_type=IssueType.BUG,
            status=WorkflowState.OPEN,
            priority=IssuePriority.MEDIUM,
            severity=IssueSeverity.CRITICAL,
            project_id=proj.id,
            reporter_id=admin_user.id,
            assignee_id=admin_user.id
        )
        i7 = Issue(
            issue_key="BUG-7",
            title="ERROR OR LOGIN WITH SPECIAL CHARACRES",
            description="Duplicate crash reporter log.",
            issue_type=IssueType.BUG,
            status=WorkflowState.OPEN,
            priority=IssuePriority.MEDIUM,
            severity=IssueSeverity.CRITICAL,
            project_id=proj.id,
            reporter_id=admin_user.id,
            assignee_id=admin_user.id
        )

        db.add_all([i1, i2, i3, i4, i5, i6, i7])
        db.commit()

        print("Database successfully seeded.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()
