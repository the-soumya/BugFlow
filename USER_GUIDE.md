# 📖 BugFlow Platform — Comprehensive User Guide

Welcome to the **BugFlow** User Guide. This document provides step-by-step instructions for engineers, testers, project managers, and administrators on navigating and utilizing the BugFlow platform.

---

## 🔑 1. User Roles & Permissions

BugFlow uses strict Role-Based Access Control (RBAC):

| Role | Responsibilities & Access Permissions |
| :--- | :--- |
| `ADMIN` | System administrator with full access to project creation, user management, audit trails, and configuration. |
| `PROJECT_MANAGER` | Oversees projects, creates sprints, assigns issues, and monitors developer workload balance. |
| `DEVELOPER` | Resolves assigned defects, updates issue states (`IN_PROGRESS`, `RESOLVED`), and tracks personal MTTR. |
| `TESTER` | Logs defects, conducts QA verification on fixed bugs, closes verified issues or reopens regressions. |
| `USER` | Submits bug reports and feature requests; reads issue status updates. |

### Default Test Accounts
- **Admin**: `admin@bugflow.com` / `password123`
- **Project Manager**: `pm@bugflow.com` / `password123`
- **Developer**: `alice@bugflow.com` / `password123`
- **Tester**: `tester@bugflow.com` / `password123`

---

## 🐞 2. Reporting & Triaging Issues

### Reporting a New Bug
1. Navigate to **Report Issue** from the sidebar.
2. Enter a descriptive **Title** (e.g., `Error on Login with Special Characters`).
3. Select the **Project**, **Issue Type** (`BUG`, `FEATURE`, `TASK`), and **Initial Severity** (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
4. Provide structured **Steps to Reproduce**, **Expected Behavior**, and **Actual Behavior**.
5. Click **Submit Issue**.

### Smart Triage & Priority Scoring
BugFlow automatically computes a dynamic **Priority Score**:
$$\text{Priority Score} = \text{Severity Weight} \times \text{Category Urgency Weight}$$

- **Critical Security Defect**: $4 \times 3 = 12.0$ (Assigned `URGENT` / `CRITICAL` priority)
- **UI Alignment Cosmetic**: $1 \times 1 = 1.0$ (Assigned `LOW` priority)

The built-in **Smart Developer Matcher** recommends the best engineer based on domain keywords and current active workload.

---

## 🏃 3. Agile Sprints & Kanban Board

### Managing Sprints
1. Navigate to **Sprints & Workflow**.
2. Select your active sprint to view the interactive Kanban Board:
   - `REPORTED` &rarr; `TRIAGED` &rarr; `IN_PROGRESS` &rarr; `QA_VERIFICATION` &rarr; `RESOLVED` &rarr; `CLOSED`
3. Drag and drop issue cards or click the quick status transition buttons.
4. Review **Sprint Burndown** and **Team Velocity** metrics upon sprint completion.

---

## 🤖 4. CI/CD Git Commit Webhook Integration

Developers can resolve issues directly through standard Git commit messages:
```bash
git commit -m "Fix password parsing edge case; fixes #2"
git push origin main
```
The automated CI/CD webhook (`POST /api/v1/webhooks/git`) intercepts the commit and:
1. Automatically advances `BUG-2` to `QA_VERIFICATION`.
2. Records the Git commit hash and author in the immutable audit trail.
3. Notifies the QA tester for verification.

---

## 🧑‍💼 5. Team Productivity & Developer Workload Matrix

Project Managers and Team Leads can monitor capacity in real-time under **Milestone 4: Optimization & Finalization**:

### Key Matrix Metrics
- **Active Tasks**: Count of open bugs actively being worked on (`IN_PROGRESS`).
- **Completed Fixes**: Count of successfully resolved and verified defects (`RESOLVED`, `CLOSED`).
- **Individual MTTR**: Average turnaround speed per developer in hours and days.
- **Resource Balance Status**:
  - `OVERLOADED` (&ge; 4 active tasks): Risk of burnout; requires task rebalancing.
  - `OPTIMAL` (2–3 active tasks): Ideal engineering throughput.
  - `LIGHT` (1 active task): Available for backlog assignment.
  - `AVAILABLE` (0 active tasks): Ready for immediate critical defect assignment.
- **Rebalance Action**: One-click redistribution of tasks to available team members.

---

## 📊 6. Quality Analytics & Executive Reports

Located under **Analytics & APIs** and **Optimization & Ops**:

- **Bug Fix Rate**: Percentage of reported defects resolved (Monthly target: 85%).
- **Average Fix Time (MTTR)**: Mean time to resolution across the organization (Target: 2.5 days).
- **Testing Code Coverage**: Automated Pytest verification (92% target).
- **Backlog Health Score**: Overall health score (0–100) based on severity weights.
- **Interactive Plotly Visualizations**: Defect inflow/outflow, severity distributions, and MTTR vs. SLA compliance.
- **Executive Exports**:
  - Click **Export PDF Report** for a formal board-ready document.
  - Click **Export CSV** for Excel-ready raw bug records with UTF-8 BOM encoding.
