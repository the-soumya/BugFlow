import re
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User, UserRole
from app.models.issue import Issue, WorkflowState

# =========================================================================
# PART 1: SMART PRIORITY CALCULATOR
# =========================================================================

SEVERITY_WEIGHTS: Dict[str, int] = {
    "CRITICAL": 4,
    "MAJOR": 3,
    "HIGH": 3,
    "MEDIUM": 2,
    "MINOR": 2,
    "LOW": 1,
    "TRIVIAL": 1,
}

CATEGORY_URGENCY_MAP: Dict[str, int] = {
    # High Urgency (3 points)
    "SECURITY": 3,
    "SECURITY VULNERABILITY": 3,
    "DATABASE": 3,
    "DATA INTEGRITY": 3,
    "AUTH": 3,
    "CRASH": 3,
    # Medium Urgency (2 points)
    "API": 2,
    "BACKEND": 2,
    "PERFORMANCE": 2,
    "INTEGRATION": 2,
    "NETWORK": 2,
    # Low Urgency (1 point)
    "UI": 1,
    "UI COLORS": 1,
    "TYPOS": 1,
    "TYPO": 1,
    "FRONTEND": 1,
    "DOCUMENTATION": 1,
    "COSMETIC": 1,
    "GENERAL": 1,
}

def resolve_category_urgency(category_str: str) -> Tuple[int, str]:
    cat = (category_str or "").strip().upper()
    
    # Direct lookup
    if cat in CATEGORY_URGENCY_MAP:
        return CATEGORY_URGENCY_MAP[cat], cat
        
    # Substring matching
    if any(k in cat for k in ["SECURITY", "DATABASE", "SQL", "POSTGRES", "DATA", "VULNERAB"]):
        return 3, "High Urgency (Security/Database)"
    if any(k in cat for k in ["API", "BACKEND", "SERVER", "PERF", "NETWORK"]):
        return 2, "Medium Urgency (API/Backend)"
    if any(k in cat for k in ["UI", "COLOR", "TYPO", "FONT", "COSMETIC", "STYLE", "FRONT"]):
        return 1, "Low Urgency (UI/Typos)"
        
    return 1, "Low Urgency (General)"

def calculate_priority_score(severity: str, category: str) -> Dict[str, Any]:
    sev_upper = (severity or "MEDIUM").strip().upper()
    sev_weight = SEVERITY_WEIGHTS.get(sev_upper, 2)
    
    urgency_weight, resolved_cat = resolve_category_urgency(category)
    
    score = float(sev_weight * urgency_weight)
    
    # Final Priority Result:
    # Score >= 10 -> URGENT
    # Score between 7 - 9 -> HIGH
    # Score between 4 - 6 -> MEDIUM
    # Score < 4 -> LOW
    if score >= 10:
        recommended_priority = "URGENT"
    elif score >= 7:
        recommended_priority = "HIGH"
    elif score >= 4:
        recommended_priority = "MEDIUM"
    else:
        recommended_priority = "LOW"
        
    return {
        "priority_score": score,
        "recommended_priority": recommended_priority,
        "severity": sev_upper,
        "severity_weight": sev_weight,
        "category": category,
        "category_urgency_weight": urgency_weight,
        "formula": f"{sev_weight} (Severity Weight) × {urgency_weight} (Category Urgency Weight) = {score}"
    }


# =========================================================================
# PART 2: SMART DEVELOPER MATCHER
# =========================================================================

# Domain keyword clusters
KEYWORD_DOMAINS = {
    "database": ["database", "sql", "postgres", "postgresql", "query", "timeout", "pool", "connection", "migration", "deadlock", "db"],
    "security": ["security", "vulnerability", "auth", "login", "password", "jwt", "token", "hash", "session", "ssl", "oauth"],
    "backend": ["api", "backend", "endpoint", "fastapi", "python", "service", "crud", "payload", "server", "http", "rest"],
    "frontend": ["ui", "css", "color", "layout", "button", "sidebar", "responsive", "browser", "react", "html", "typo", "display", "frontend", "modal"],
    "qa": ["qa", "testing", "locust", "load", "benchmark", "automation", "regression", "flaky", "verify"]
}

def recommend_developers(db: Session, title: str, description: str, limit: int = 3) -> List[Dict[str, Any]]:
    # 1. Search words in title and description
    full_text = f"{title or ''} {description or ''}".lower()
    tokens = set(re.findall(r'\b[a-z0-9_#-]+\b', full_text))
    
    # Detect matched domains in text
    detected_domains = []
    matched_keywords = []
    for domain, kws in KEYWORD_DOMAINS.items():
        for kw in kws:
            if kw in full_text:
                matched_keywords.append(kw)
                if domain not in detected_domains:
                    detected_domains.append(domain)

    # 2. Query technical developers / users
    # Users with DEVELOPER, ADMIN, PROJECT_MANAGER, or TESTER who are active
    users = db.query(User).filter(
        User.active == True,
        User.role.in_([UserRole.DEVELOPER, UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TESTER])
    ).all()

    # 3. Check workload for each developer: count active open bugs assigned
    # Active bugs = status not in ('RESOLVED', 'CLOSED')
    active_statuses = [
        WorkflowState.REPORTED,
        WorkflowState.TRIAGED,
        WorkflowState.OPEN,
        WorkflowState.IN_PROGRESS,
        WorkflowState.QA_VERIFICATION,
        WorkflowState.REOPENED
    ]
    
    scored_devs = []
    for user in users:
        # Workload count
        workload = db.query(Issue).filter(
            Issue.assignee_id == user.id,
            Issue.status.in_(active_statuses)
        ).count()
        
        # Skills text from user profile
        user_skills_str = (user.skills or "").lower()
        user_skills_list = [s.strip() for s in user_skills_str.split(",") if s.strip()]
        
        # Calculate skill score
        skill_hits = 0
        matching_skill_names = []
        for s in user_skills_list:
            # Check if skill matches any detected keywords or full text tokens
            if s in full_text or any(token in s for token in tokens if len(token) > 2):
                skill_hits += 1
                matching_skill_names.append(s.title())
            elif any(s in kw_list for domain in detected_domains for kw_list in [KEYWORD_DOMAINS[domain]]):
                skill_hits += 1
                matching_skill_names.append(s.title())
                
        # Primary base match percentage
        if skill_hits > 0:
            # High relevant match
            base_percentage = 70 + min(skill_hits * 12, 25)
        elif any(d in user_skills_str for d in detected_domains):
            base_percentage = 65
        else:
            # General fallback match
            base_percentage = 45 if user.role == UserRole.DEVELOPER else 35

        # Workload deduction: don't give 10 bugs to one person if someone else is free!
        # -4% per active bug, capped at -30%
        workload_penalty = min(workload * 4, 30)
        final_percentage = max(15, min(98, base_percentage - workload_penalty))
        
        # Build human-friendly rationale string
        active_task_str = f"{workload} active task" if workload == 1 else f"{workload} active tasks"
        if matching_skill_names:
            expert_area = f"{', '.join(matching_skill_names[:2])} expert"
            rationale = f"{user.name} - {final_percentage}% match ({expert_area}, {active_task_str})"
        elif skill_hits > 0 or user_skills_list:
            top_skill = user_skills_list[0].title() if user_skills_list else "Generalist"
            rationale = f"{user.name} - {final_percentage}% match ({top_skill}, {active_task_str})"
        else:
            rationale = f"{user.name} - {final_percentage}% match (Available developer, {active_task_str})"

        scored_devs.append({
            "developer_id": user.id,
            "name": user.name,
            "email": user.email,
            "skills": user.skills or "General Engineering",
            "match_percentage": int(final_percentage),
            "active_tasks": workload,
            "rationale": rationale,
            "skill_hits": skill_hits
        })

    # Sort descending by match percentage, then ascending by workload
    scored_devs.sort(key=lambda x: (x["match_percentage"], -x["active_tasks"]), reverse=True)
    
    return scored_devs[:limit]
