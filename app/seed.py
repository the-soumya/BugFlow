from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.issue import Issue, IssueType, WorkflowState, IssuePriority, IssueSeverity
from app.models.sprint import Sprint, SprintStatus
from app.models.collaboration import Comment
from app.models.audit_log import AuditLog
from app.security import get_password_hash
from datetime import datetime, timedelta

DEVELOPER_SKILLS_MAP = {
    "admin@bugflow.com": "System Administration, DevOps, Security, Docker, Linux",
    "pm@bugflow.com": "Project Management, Python, PostgreSQL, Database, Security",
    "dev@bugflow.com": "Python, FastAPI, PostgreSQL, Database, Backend, Performance",
    "tester@bugflow.com": "QA, Testing, Locust, Load Testing, Automation, Regression",
    "user@bugflow.com": "Frontend, React, CSS, HTML, UI/UX, Design, Dashboard"
}

def seed_data():
    db = SessionLocal()
    try:
        print("Checking BugFlow seed data...")

        # 1. Update or create users
        hashed_pwd = get_password_hash("password123")
        users_in_db = {u.email: u for u in db.query(User).all()}

        if not users_in_db:
            print("Creating default users...")
            admin_user = User(name="System Administrator", email="admin@bugflow.com", password=hashed_pwd, role=UserRole.ADMIN, skills=DEVELOPER_SKILLS_MAP["admin@bugflow.com"])
            pm_user = User(name="John Doe", email="pm@bugflow.com", password=hashed_pwd, role=UserRole.PROJECT_MANAGER, skills=DEVELOPER_SKILLS_MAP["pm@bugflow.com"])
            dev_user = User(name="Alex Rivera", email="dev@bugflow.com", password=hashed_pwd, role=UserRole.DEVELOPER, skills=DEVELOPER_SKILLS_MAP["dev@bugflow.com"])
            tester_user = User(name="Bruce Wayne", email="tester@bugflow.com", password=hashed_pwd, role=UserRole.TESTER, skills=DEVELOPER_SKILLS_MAP["tester@bugflow.com"])
            std_user = User(name="Taylor Kim", email="user@bugflow.com", password=hashed_pwd, role=UserRole.USER, skills=DEVELOPER_SKILLS_MAP["user@bugflow.com"])

            db.add_all([admin_user, pm_user, dev_user, tester_user, std_user])
            db.commit()
            for u in [admin_user, pm_user, dev_user, tester_user, std_user]:
                db.refresh(u)
            users_in_db = {u.email: u for u in [admin_user, pm_user, dev_user, tester_user, std_user]}
        else:
            # Update skills on existing users
            for email, skills in DEVELOPER_SKILLS_MAP.items():
                if email in users_in_db and not users_in_db[email].skills:
                    users_in_db[email].skills = skills
            db.commit()

        admin_user = users_in_db.get("admin@bugflow.com")
        pm_user = users_in_db.get("pm@bugflow.com")
        dev_user = users_in_db.get("dev@bugflow.com")
        tester_user = users_in_db.get("tester@bugflow.com")
        std_user = users_in_db.get("user@bugflow.com")

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

        # 4. Check issues and attach category, sprint, priority score
        issues = db.query(Issue).filter(Issue.project_id == proj.id).all()
        if not issues:
            # Create issues matching mockup
            i1 = Issue(
                issue_key="BUG-1",
                title="Minor UI Glitch on Dashboard sidebar",
                description="The sidebar overflows on 13 inch laptop displays.",
                issue_type=IssueType.BUG,
                status=WorkflowState.REPORTED,
                priority=IssuePriority.LOW,
                severity=IssueSeverity.LOW,
                category="UI Colors",
                priority_score=1.0,
                sprint_id=sprint1.id,
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
                priority=IssuePriority.URGENT,
                severity=IssueSeverity.CRITICAL,
                category="Security",
                priority_score=12.0,
                sprint_id=sprint1.id,
                project_id=proj.id,
                reporter_id=pm_user.id,
                assignee_id=dev_user.id
            )
            i3 = Issue(
                issue_key="BUG-3",
                title="PostgreSQL connection pool exhaustion under 200 req/s load",
                description="Database connections hang when load testing is run using Locust.",
                issue_type=IssueType.BUG,
                status=WorkflowState.REPORTED,
                priority=IssuePriority.HIGH,
                severity=IssueSeverity.HIGH,
                category="Database",
                priority_score=9.0,
                sprint_id=None, # In Backlog!
                project_id=proj.id,
                reporter_id=tester_user.id,
                assignee_id=None
            )
            i4 = Issue(
                issue_key="BUG-4",
                title="Validate JWT token revocation and expiry edge cases",
                description="Verify blacklisting works for expired tokens.",
                issue_type=IssueType.TASK,
                status=WorkflowState.RESOLVED,
                priority=IssuePriority.URGENT,
                severity=IssueSeverity.CRITICAL,
                category="Security",
                priority_score=12.0,
                sprint_id=sprint1.id,
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
                status=WorkflowState.REPORTED,
                priority=IssuePriority.MEDIUM,
                severity=IssueSeverity.LOW,
                category="UI",
                priority_score=2.0,
                sprint_id=None, # In Backlog!
                project_id=proj.id,
                reporter_id=std_user.id,
                assignee_id=None
            )
            i6 = Issue(
                issue_key="BUG-6",
                title="Database timeout on concurrent transaction commits",
                description="Auto-generated triage issue from crash reporter log on DB pool.",
                issue_type=IssueType.BUG,
                status=WorkflowState.TRIAGED,
                priority=IssuePriority.HIGH,
                severity=IssueSeverity.HIGH,
                category="Database",
                priority_score=9.0,
                sprint_id=None, # In Backlog!
                project_id=proj.id,
                reporter_id=admin_user.id,
                assignee_id=dev_user.id
            )
            db.add_all([i1, i2, i3, i4, i5, i6])
            db.commit()
            issues = [i1, i2, i3, i4, i5, i6]
        else:
            # Update existing issues with sprint_id, category and priority_score if null
            for i in issues:
                if not i.category:
                    if "database" in i.title.lower() or "pool" in i.title.lower():
                        i.category = "Database"
                        i.priority_score = 9.0
                    elif "login" in i.title.lower() or "jwt" in i.title.lower() or "password" in i.title.lower():
                        i.category = "Security"
                        i.priority_score = 12.0
                        i.priority = IssuePriority.URGENT
                    elif "sidebar" in i.title.lower() or "ui" in i.title.lower():
                        i.category = "UI Colors"
                        i.priority_score = 2.0
                    else:
                        i.category = "General"
                        i.priority_score = 4.0
                
                # If sprint_id is None, place first 2 into sprint1
                if i.sprint_id is None and i.issue_key in ["BUG-1", "BUG-2", "BUG-4"]:
                    i.sprint_id = sprint1.id
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

        print("Database successfully seeded with Core Platform and Agile Collaboration data.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
