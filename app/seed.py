from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.issue import Issue, IssueType, WorkflowState, IssuePriority, IssueSeverity
from app.models.sprint import Sprint, SprintStatus
from app.models.collaboration import Comment
from app.models.audit_log import AuditLog
from app.security import get_password_hash
from datetime import datetime, timedelta

DEVELOPER_SEED_DATA = [
    {
        "name": "System Administrator",
        "email": "admin@bugflow.com",
        "role": UserRole.ADMIN,
        "team": "DevOps & SRE",
        "skills": "System Administration, DevOps, Security, Docker, Linux, Kubernetes"
    },
    {
        "name": "John Doe",
        "email": "pm@bugflow.com",
        "role": UserRole.PROJECT_MANAGER,
        "team": "Backend Engineering",
        "skills": "Project Management, Python, PostgreSQL, Database, Security, Architecture"
    },
    {
        "name": "Alice Smith",
        "email": "alice@bugflow.com",
        "role": UserRole.DEVELOPER,
        "team": "Frontend UI",
        "skills": "React, TypeScript, CSS3, Webpack, Responsive Design, State Management"
    },
    {
        "name": "Bruce Wayne",
        "email": "tester@bugflow.com",
        "role": UserRole.TESTER,
        "team": "Security & QA",
        "skills": "Penetration Testing, Security Auditing, Locust, Load Testing, QA Automation"
    },
    {
        "name": "Alex Rivera",
        "email": "dev@bugflow.com",
        "role": UserRole.DEVELOPER,
        "team": "Backend Engineering",
        "skills": "Python, FastAPI, PostgreSQL, Database, Backend, Performance, SQLAlchemy"
    },
    {
        "name": "Taylor Kim",
        "email": "user@bugflow.com",
        "role": UserRole.USER,
        "team": "Frontend UI",
        "skills": "Frontend, UI/UX, Design Systems, HTML5, Dashboard Analytics"
    }
]

def seed_data():
    from sqlalchemy import text
    
    # 1. Ensure all tables exist
    Base.metadata.create_all(bind=engine)
    
    # 2. Ensure schema columns and indexes exist in PostgreSQL/SQLite
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS team VARCHAR(100) DEFAULT 'Backend Engineering';"))
            conn.commit()
        except Exception:
            pass
        
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_issue_project_status ON issues (project_id, status);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_issue_assignee_status ON issues (assignee_id, status);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_issue_created_at ON issues (created_at);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_issue_sprint_status ON issues (sprint_id, status);"))
            conn.commit()
        except Exception:
            pass
    
    db = SessionLocal()
    try:
        print("Checking BugFlow seed data for Milestone 4...")


        hashed_pwd = get_password_hash("password123")
        users_in_db = {u.email: u for u in db.query(User).all()}

        # 1. Update or create users with teams
        for u_data in DEVELOPER_SEED_DATA:
            email = u_data["email"]
            if email not in users_in_db:
                new_user = User(
                    name=u_data["name"],
                    email=email,
                    password=hashed_pwd,
                    role=u_data["role"],
                    team=u_data["team"],
                    skills=u_data["skills"],
                    active=True
                )
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
                users_in_db[email] = new_user
            else:
                user = users_in_db[email]
                updated = False
                if not getattr(user, 'team', None) or user.team != u_data["team"]:
                    user.team = u_data["team"]
                    updated = True
                if not getattr(user, 'skills', None):
                    user.skills = u_data["skills"]
                    updated = True
                if updated:
                    db.commit()

        admin_user = users_in_db.get("admin@bugflow.com")
        pm_user = users_in_db.get("pm@bugflow.com") # John Doe
        alice_user = users_in_db.get("alice@bugflow.com") # Alice Smith
        tester_user = users_in_db.get("tester@bugflow.com") # Bruce Wayne
        dev_user = users_in_db.get("dev@bugflow.com") # Alex Rivera
        std_user = users_in_db.get("user@bugflow.com") # Taylor Kim

        # 2. Check / create project
        proj = db.query(Project).first()
        if not proj:
            proj = Project(
                name="Mobile Reporter App",
                description="BugFlow Native Client for field reporters, featuring crash reporting and offline sync.",
                project_key="BUG",
                created_by_id=admin_user.id
            )
            db.add(proj)
            db.commit()
            db.refresh(proj)

        # 3. Check / create default Sprint
        sprint1 = db.query(Sprint).filter(Sprint.name == "Sprint 1 - Foundation").first()
        if not sprint1:
            sprint1 = Sprint(
                project_id=proj.id,
                name="Sprint 1 - Foundation",
                goal="Implement core database schemas, triage automation, and initial defect fixes.",
                start_date=datetime.utcnow() - timedelta(days=5),
                end_date=datetime.utcnow() + timedelta(days=9),
                status=SprintStatus.ACTIVE,
                velocity=0
            )
            db.add(sprint1)
            db.commit()
            db.refresh(sprint1)

        # 4. Check issues and attach category, sprint, priority score, and assigned workloads
        existing_issues = {i.issue_key: i for i in db.query(Issue).filter(Issue.project_id == proj.id).all()}
        now = datetime.utcnow()

        sample_issues = [
            {
                "issue_key": "BUG-1",
                "title": "Minor UI Glitch on Dashboard sidebar",
                "description": "The sidebar overflows on 13 inch laptop displays.",
                "issue_type": IssueType.BUG,
                "status": WorkflowState.RESOLVED,
                "priority": IssuePriority.LOW,
                "severity": IssueSeverity.LOW,
                "category": "UI Colors",
                "priority_score": 1.0,
                "sprint_id": sprint1.id,
                "reporter_id": std_user.id,
                "assignee_id": alice_user.id if alice_user else dev_user.id,
                "created_at": now - timedelta(hours=36),
                "resolved_at": now - timedelta(hours=12)
            },
            {
                "issue_key": "BUG-2",
                "title": "Error on Login with Special Characters in Password",
                "description": "B-002: Login button does not respond if the password contains '#', '&', or '%'.",
                "issue_type": IssueType.BUG,
                "status": WorkflowState.IN_PROGRESS,
                "priority": IssuePriority.URGENT,
                "severity": IssueSeverity.CRITICAL,
                "category": "Security",
                "priority_score": 12.0,
                "sprint_id": sprint1.id,
                "reporter_id": pm_user.id,
                "assignee_id": dev_user.id,
                "created_at": now - timedelta(hours=20),
                "resolved_at": None
            },
            {
                "issue_key": "BUG-3",
                "title": "PostgreSQL connection pool exhaustion under 200 req/s load",
                "description": "Database connections hang when load testing is run using Locust.",
                "issue_type": IssueType.BUG,
                "status": WorkflowState.IN_PROGRESS,
                "priority": IssuePriority.HIGH,
                "severity": IssueSeverity.HIGH,
                "category": "Database",
                "priority_score": 9.0,
                "sprint_id": sprint1.id,
                "reporter_id": tester_user.id,
                "assignee_id": pm_user.id, # John Doe
                "created_at": now - timedelta(hours=28),
                "resolved_at": None
            },
            {
                "issue_key": "BUG-4",
                "title": "Validate JWT token revocation and expiry edge cases",
                "description": "Verify blacklisting works for expired tokens.",
                "issue_type": IssueType.TASK,
                "status": WorkflowState.RESOLVED,
                "priority": IssuePriority.URGENT,
                "severity": IssueSeverity.CRITICAL,
                "category": "Security",
                "priority_score": 12.0,
                "sprint_id": sprint1.id,
                "reporter_id": admin_user.id,
                "assignee_id": pm_user.id, # John Doe
                "created_at": now - timedelta(hours=48),
                "resolved_at": now - timedelta(hours=6)
            },
            {
                "issue_key": "BUG-5",
                "title": "Sidebar does not remember collapse state on refresh",
                "description": "User has to click collapse every time they reload.",
                "issue_type": IssueType.ENHANCEMENT,
                "status": WorkflowState.IN_PROGRESS,
                "priority": IssuePriority.MEDIUM,
                "severity": IssueSeverity.LOW,
                "category": "UI",
                "priority_score": 2.0,
                "sprint_id": sprint1.id,
                "reporter_id": std_user.id,
                "assignee_id": alice_user.id if alice_user else dev_user.id,
                "created_at": now - timedelta(hours=14),
                "resolved_at": None
            },
            {
                "issue_key": "BUG-6",
                "title": "Database timeout on concurrent transaction commits",
                "description": "Auto-generated triage issue from crash reporter log on DB pool.",
                "issue_type": IssueType.BUG,
                "status": WorkflowState.RESOLVED,
                "priority": IssuePriority.HIGH,
                "severity": IssueSeverity.HIGH,
                "category": "Database",
                "priority_score": 9.0,
                "sprint_id": sprint1.id,
                "reporter_id": admin_user.id,
                "assignee_id": dev_user.id,
                "created_at": now - timedelta(hours=50),
                "resolved_at": now - timedelta(hours=10)
            },
            {
                "issue_key": "BUG-7",
                "title": "Automated regression testing failure on OAuth callback",
                "description": "Environment: Production. OAuth2 callback times out intermittently.",
                "issue_type": IssueType.BUG,
                "status": WorkflowState.IN_PROGRESS,
                "priority": IssuePriority.HIGH,
                "severity": IssueSeverity.HIGH,
                "category": "Security",
                "priority_score": 8.5,
                "sprint_id": sprint1.id,
                "reporter_id": admin_user.id,
                "assignee_id": tester_user.id, # Bruce Wayne
                "created_at": now - timedelta(hours=18),
                "resolved_at": None
            },
            {
                "issue_key": "BUG-8",
                "title": "Fix contrast ratio on dark mode navigation items",
                "description": "Accessibility compliance requires 4.5:1 contrast on all nav links.",
                "issue_type": IssueType.ENHANCEMENT,
                "status": WorkflowState.RESOLVED,
                "priority": IssuePriority.LOW,
                "severity": IssueSeverity.TRIVIAL,
                "category": "UI Colors",
                "priority_score": 1.5,
                "sprint_id": sprint1.id,
                "reporter_id": pm_user.id,
                "assignee_id": alice_user.id if alice_user else dev_user.id,
                "created_at": now - timedelta(hours=30),
                "resolved_at": now - timedelta(hours=15)
            }
        ]

        for s_issue in sample_issues:
            key = s_issue["issue_key"]
            if key not in existing_issues:
                new_iss = Issue(
                    project_id=proj.id,
                    **s_issue
                )
                db.add(new_iss)
            else:
                iss = existing_issues[key]
                # Update fields
                for k, v in s_issue.items():
                    if k != "issue_key":
                        setattr(iss, k, v)
        db.commit()

        # 5. Seed sample comments
        bug2 = db.query(Issue).filter(Issue.issue_key == "BUG-2").first()
        if bug2:
            comment_count = db.query(Comment).filter(Comment.issue_id == bug2.id).count()
            if comment_count == 0:
                c1 = Comment(
                    issue_id=bug2.id,
                    user_id=dev_user.id if dev_user else None,
                    content="I reproduced this bug on Chrome v120 with password containing '#$%'",
                    created_at=datetime.utcnow() - timedelta(hours=2)
                )
                c2 = Comment(
                    issue_id=bug2.id,
                    user_id=pm_user.id if pm_user else None,
                    content="Thanks Alex, please ensure this is prioritized for Sprint 1.",
                    created_at=datetime.utcnow() - timedelta(hours=1)
                )
                db.add_all([c1, c2])
                db.commit()

        print("Database successfully seeded with Core Platform, Agile, and Milestone 4 Workload data.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()

