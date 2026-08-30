// State variables
let token = localStorage.getItem("bugflow_token") || "";
let currentUser = null;
let activeProjectId = null;
let projects = [];
let users = [];
let currentPage = 0;
let pageSize = 10;

// Chart references
let charts = {
    status: null,
    priority: null,
    severity: null,
    type: null
};

// Simulated default users for dropdown selector (will be seeded in DB)
const SIMULATED_USERS = [
    { email: "admin@bugflow.com", label: "Admin (System Admin)" },
    { email: "pm@bugflow.com", label: "PM (Project Manager)" },
    { email: "dev@bugflow.com", label: "Dev (Developer)" },
    { email: "tester@bugflow.com", label: "Tester (QA/Tester)" },
    { email: "user@bugflow.com", label: "User (Standard User)" }
];

// Document Ready
document.addEventListener("DOMContentLoaded", () => {
    initApp();
    setupEventListeners();
});

// Initialize Application State
async function initApp() {
    if (token) {
        try {
            // Validate token & get active user
            const response = await apiRequest("/api/auth/users", "GET");
            if (response.success) {
                // Parse JWT to extract profile info
                const payload = parseJwt(token);
                currentUser = {
                    email: payload.sub,
                    role: payload.role,
                    name: payload.name
                };

                // Show Main App, hide login
                document.getElementById("auth-page").style.display = "none";
                document.getElementById("main-app").style.display = "flex";

                // Update profile cards
                updateUserProfileUI();

                // Load core data
                await loadProjects();
                await loadUsers();

                // Go to Dashboard by default
                switchView("dashboard-view");
            } else {
                logout();
            }
        } catch (err) {
            console.error("Auth validation failed", err);
            logout();
        }
    } else {
        // Show Login screen
        document.getElementById("auth-page").style.display = "flex";
        document.getElementById("main-app").style.display = "none";
    }
}

// Setup Event Listeners
function setupEventListeners() {
    // Auth switching links
    document.getElementById("switch-to-register").addEventListener("click", (e) => {
        e.preventDefault();
        document.getElementById("login-form").classList.remove("active");
        document.getElementById("register-form").classList.add("active");
    });

    document.getElementById("switch-to-login").addEventListener("click", (e) => {
        e.preventDefault();
        document.getElementById("register-form").classList.remove("active");
        document.getElementById("login-form").classList.add("active");
    });

    // Auth Form submissions
    document.getElementById("login-form").addEventListener("submit", handleLogin);
    document.getElementById("register-form").addEventListener("submit", handleRegister);
    document.getElementById("btn-logout").addEventListener("click", logout);

    // Sidebar navigation routes
    document.querySelectorAll(".sidebar-nav .nav-item").forEach(item => {
        item.addEventListener("click", (e) => {
            if (item.classList.contains("disabled")) return;
            e.preventDefault();
            const viewId = item.getAttribute("data-view");
            switchView(viewId);
        });
    });

    // Dashboard Project Selector Change
    document.getElementById("issue-project-select").addEventListener("change", (e) => {
        activeProjectId = parseInt(e.target.value);
        localStorage.setItem("bugflow_active_project", activeProjectId);
        // Sync other project selectors
        syncProjectSelectors(activeProjectId);
        loadDashboardIssues();
    });

    // Issues View Project Filter Selector Change
    document.getElementById("issues-filter-project").addEventListener("change", (e) => {
        activeProjectId = parseInt(e.target.value);
        localStorage.setItem("bugflow_active_project", activeProjectId);
        syncProjectSelectors(activeProjectId);
        currentPage = 0;
        loadIssuesGrid();
    });

    // Issues View other filters
    document.getElementById("issues-filter-status").addEventListener("change", () => {
        currentPage = 0;
        loadIssuesGrid();
    });
    document.getElementById("issues-filter-priority").addEventListener("change", () => {
        currentPage = 0;
        loadIssuesGrid();
    });
    document.getElementById("issues-grid-search").addEventListener("input", debounce(loadIssuesGrid, 300));
    document.getElementById("dashboard-issue-search").addEventListener("input", debounce(loadDashboardIssues, 300));

    // Dashboard Create Issue
    document.getElementById("dashboard-create-issue-form").addEventListener("submit", handleCreateIssueFromDashboard);

    // Standalone Create Issue
    document.getElementById("standalone-create-issue-form").addEventListener("submit", handleCreateIssueStandalone);

    // Project Create Form
    document.getElementById("project-create-form").addEventListener("submit", handleCreateProject);

    // Dashboard Refresh button
    document.getElementById("btn-refresh-dashboard").addEventListener("click", () => {
        loadDashboardIssues();
    });

    // Duplicate Check Warning on Title input in dashboard
    document.getElementById("issue-title-input").addEventListener("input", checkPotentialDuplicateTitle);

    // User Simulation Switcher
    document.getElementById("simulated-user-select").addEventListener("change", handleSimulatedUserSwitch);

    // Trigger New Issue from Issues view
    document.getElementById("btn-new-issue-trigger").addEventListener("click", () => {
        switchView("new-issue-view");
    });

    // Pagination Click events
    document.getElementById("btn-page-prev").addEventListener("click", () => {
        if (currentPage > 0) {
            currentPage--;
            loadIssuesGrid();
        }
    });
    document.getElementById("btn-page-next").addEventListener("click", () => {
        currentPage++;
        loadIssuesGrid();
    });

    // Modal Close
    document.getElementById("btn-close-modal").addEventListener("click", () => {
        document.getElementById("issue-detail-modal").style.display = "none";
    });

    // Modal Assignment change save
    document.getElementById("btn-save-assignment").addEventListener("click", handleSaveAssignment);

    // Project Select in Reports
    document.getElementById("reports-project-select").addEventListener("change", (e) => {
        const pId = parseInt(e.target.value);
        loadReportsView(pId);
    });
}

// ================= AUTHENTICATION ACTIONS =================
async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;

    try {
        const response = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });
        const res = await response.json();

        if (res.success) {
            token = res.data.token;
            localStorage.setItem("bugflow_token", token);
            document.getElementById("login-form").reset();
            await initApp();
        } else {
            alert("Login failed: " + res.message);
        }
    } catch (err) {
        console.error(err);
        alert("An error occurred during sign in.");
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const name = document.getElementById("register-name").value;
    const email = document.getElementById("register-email").value;
    const password = document.getElementById("register-password").value;
    const role = document.getElementById("register-role").value;

    try {
        const response = await fetch("/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, email, password, role })
        });
        const res = await response.json();

        if (res.success) {
            alert("Registration successful! Please login.");
            document.getElementById("register-form").reset();
            document.getElementById("register-form").classList.remove("active");
            document.getElementById("login-form").classList.add("active");
        } else {
            alert("Registration failed: " + res.message);
        }
    } catch (err) {
        console.error(err);
        alert("An error occurred during registration.");
    }
}

function logout() {
    token = "";
    currentUser = null;
    localStorage.removeItem("bugflow_token");
    localStorage.removeItem("bugflow_active_project");

    // Reset views
    document.getElementById("auth-page").style.display = "flex";
    document.getElementById("main-app").style.display = "none";
}

// Simulated Switching (Logs in dynamically with matching role)
async function handleSimulatedUserSwitch(e) {
    const email = e.target.value;
    if (!email) return;

    try {
        const response = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password: "password123" })
        });
        const res = await response.json();
        if (res.success) {
            token = res.data.token;
            localStorage.setItem("bugflow_token", token);
            await initApp();
        } else {
            alert("Simulation switch failed: " + res.message);
        }
    } catch (err) {
        console.error("Simulation failed", err);
    }
}

// ================= VIEW NAVIGATION =================
function switchView(viewId) {
    // Hide all views, activate target
    document.querySelectorAll(".app-view").forEach(view => {
        view.classList.remove("active");
    });
    document.getElementById(viewId).classList.add("active");

    // Toggle active menu class in sidenav
    document.querySelectorAll(".sidebar-nav .nav-item").forEach(item => {
        item.classList.remove("active");
        if (item.getAttribute("data-view") === viewId) {
            item.classList.add("active");
        }
    });

    // View specific initial loads
    if (viewId === "dashboard-view") {
        loadDashboardIssues();
    } else if (viewId === "issues-view") {
        loadIssuesGrid();
    } else if (viewId === "projects-view") {
        renderProjectsList();
    } else if (viewId === "reports-view") {
        loadReportsView(activeProjectId);
    } else if (viewId === "team-view") {
        renderTeamList();
    }
}

// ================= DATA LOADING =================
async function loadProjects() {
    const res = await apiRequest("/api/projects", "GET");
    if (res.success) {
        projects = res.data;
        populateProjectSelectors();

        // Pick active project
        const stored = localStorage.getItem("bugflow_active_project");
        if (stored && projects.some(p => p.id == stored)) {
            activeProjectId = parseInt(stored);
        } else if (projects.length > 0) {
            activeProjectId = projects[0].id;
        } else {
            activeProjectId = null;
        }

        syncProjectSelectors(activeProjectId);
    }
}

async function loadUsers() {
    const res = await apiRequest("/api/auth/users", "GET");
    if (res.success) {
        users = res.data;
        populateUserSelectors();
        populateSimulatedUserSelect();
    }
}

// ================= UI RENDERING POPULATION =================
function updateUserProfileUI() {
    if (!currentUser) return;

    // Sidebar profile
    document.getElementById("sidebar-name").innerText = currentUser.name;
    document.getElementById("sidebar-role").innerText = capitalizeRole(currentUser.role);

    const initials = currentUser.name.split(" ").map(n => n[0]).join("").substring(0, 2).toUpperCase();
    document.getElementById("sidebar-avatar").innerText = initials;

    // Header simulated status configuration
    document.getElementById("header-auth-badge").innerText =
        `Auth: Role-based configured for ${currentUser.role} (${currentUser.name})`;
}

function populateProjectSelectors() {
    const selectors = ["issue-project-select", "issues-filter-project", "standalone-project-select", "reports-project-select"];
    selectors.forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        el.innerHTML = "";

        if (id === "issues-filter-project" && projects.length === 0) {
            el.innerHTML = `<option value="">No Projects Available</option>`;
            return;
        }

        projects.forEach(p => {
            const opt = document.createElement("option");
            opt.value = p.id;
            opt.innerText = `${p.name} [${p.project_key}]`;
            el.appendChild(opt);
        });
    });
}

function populateUserSelectors() {
    const selectors = ["modal-assignee-select"];
    selectors.forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        el.innerHTML = '<option value="">Unassigned</option>';

        users.forEach(u => {
            const opt = document.createElement("option");
            opt.value = u.id;
            opt.innerText = `${u.name} (${capitalizeRole(u.role)})`;
            el.appendChild(opt);
        });
    });
}

function populateSimulatedUserSelect() {
    const select = document.getElementById("simulated-user-select");
    if (!select) return;

    select.innerHTML = '<option value="">Simulate Role (Instant Login)</option>';

    SIMULATED_USERS.forEach(su => {
        const opt = document.createElement("option");
        opt.value = su.email;
        opt.innerText = su.label;
        if (currentUser && currentUser.email === su.email) {
            opt.selected = true;
        }
        select.appendChild(opt);
    });
}

function syncProjectSelectors(projectId) {
    if (!projectId) return;
    const selectors = ["issue-project-select", "issues-filter-project", "standalone-project-select", "reports-project-select"];
    selectors.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = projectId;
    });
}

// ================= VIEW A: DASHBOARD ISSUES (IMAGE 1 STYLE) =================
async function loadDashboardIssues() {
    const listContainer = document.getElementById("dashboard-issues-list");
    if (!activeProjectId) {
        listContainer.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-folder-open"></i>
                <p>No project selected. Create or select a project to list issues.</p>
            </div>
        `;
        return;
    }

    const searchVal = document.getElementById("dashboard-issue-search").value;
    let url = `/api/projects/${activeProjectId}/issues?page=0&size=20`;

    const res = await apiRequest(url, "GET");
    if (res.success) {
        let issues = res.data.content;

        // Apply search locally for fast filtering
        if (searchVal) {
            issues = issues.filter(i =>
                i.title.toLowerCase().includes(searchVal.toLowerCase()) ||
                i.issue_key.toLowerCase().includes(searchVal.toLowerCase())
            );
        }

        if (issues.length === 0) {
            listContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-magnifying-glass"></i>
                    <p>No active issues found matching your filters.</p>
                </div>
            `;
            return;
        }

        listContainer.innerHTML = "";
        issues.forEach(i => {
            const card = document.createElement("div");
            card.className = "issue-card";
            card.addEventListener("click", () => openIssueDetailModal(i.id));

            const priorityBadge = `badge-${i.priority.toLowerCase() === 'critical' ? 'crit' : i.priority.toLowerCase() === 'high' ? 'high' : i.priority.toLowerCase() === 'medium' ? 'med' : 'low'}`;
            const severityBadge = `badge-${i.severity.toLowerCase() === 'critical' ? 'crit' : i.severity.toLowerCase() === 'high' ? 'high' : i.severity.toLowerCase() === 'medium' ? 'med' : 'low'}`;

            card.innerHTML = `
                <div class="card-details">
                    <div class="card-title-line">
                        <span class="card-key">${i.issue_key}</span>
                        <span class="card-title">${escapeHTML(i.title)}</span>
                    </div>
                    <div class="card-meta-line">
                        <span>Severity: <span class="badge ${severityBadge}">${i.severity}</span></span>
                        <span>Priority: <span class="badge ${priorityBadge}">${i.priority}</span></span>
                        <span>Assignee: <span class="text-muted">${i.assignee ? i.assignee.name : 'Unassigned'}</span></span>
                    </div>
                </div>
                <div class="card-status-col">
                    <span class="capsule capsule-${i.status.toLowerCase().replace('_', '-')}">${i.status}</span>
                </div>
            `;
            listContainer.appendChild(card);
        });
    }
}

// ================= VIEW B: ISSUES GRID TABLE (IMAGE 2 STYLE) =================
async function loadIssuesGrid() {
    const tableBody = document.getElementById("issues-table-body");
    if (!activeProjectId) {
        tableBody.innerHTML = `<tr><td colspan="9" class="empty-state"><i class="fa-solid fa-folder"></i><p>Select a project</p></td></tr>`;
        return;
    }

    const statusVal = document.getElementById("issues-filter-status").value;
    const priorityVal = document.getElementById("issues-filter-priority").value;
    const searchVal = document.getElementById("issues-grid-search").value;

    let url = `/api/projects/${activeProjectId}/issues?page=${currentPage}&size=${pageSize}`;
    if (statusVal) url += `&status=${statusVal}`;
    if (priorityVal) url += `&priority=${priorityVal}`;

    const res = await apiRequest(url, "GET");
    if (res.success) {
        let issues = res.data.content;
        const total = res.data.totalElements;
        const totalPages = res.data.totalPages;

        // Apply search filter locally if present
        if (searchVal) {
            issues = issues.filter(i =>
                i.title.toLowerCase().includes(searchVal.toLowerCase()) ||
                i.issue_key.toLowerCase().includes(searchVal.toLowerCase())
            );
        }

        if (issues.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="9" class="empty-state"><i class="fa-solid fa-clipboard-question"></i><p>No issues matching criteria</p></td></tr>`;
            updatePaginationUI(0, 0, 0);
            return;
        }

        tableBody.innerHTML = "";
        issues.forEach(i => {
            const tr = document.createElement("tr");
            tr.addEventListener("click", () => openIssueDetailModal(i.id));

            const severityBadge = `badge-${i.severity.toLowerCase() === 'critical' ? 'crit' : i.severity.toLowerCase() === 'high' ? 'high' : i.severity.toLowerCase() === 'medium' ? 'med' : 'low'}`;
            const priorityBadge = `badge-${i.priority.toLowerCase() === 'critical' ? 'crit' : i.priority.toLowerCase() === 'high' ? 'high' : i.priority.toLowerCase() === 'medium' ? 'med' : 'low'}`;

            tr.innerHTML = `
                <td class="cell-key">${i.issue_key}</td>
                <td class="cell-title">${escapeHTML(i.title)}</td>
                <td>${i.issue_type}</td>
                <td><span class="badge ${severityBadge}">${i.severity}</span></td>
                <td><span class="badge ${priorityBadge}">${i.priority}</span></td>
                <td><span class="capsule capsule-${i.status.toLowerCase().replace('_', '-')}">${i.status}</span></td>
                <td>${i.reporter ? i.reporter.name : 'Unknown'}</td>
                <td>${i.assignee ? i.assignee.name : 'Unassigned'}</td>
                <td>
                    <button class="btn btn-secondary btn-icon" onclick="event.stopPropagation(); openIssueDetailModal(${i.id})" title="View Detail">
                        <i class="fa-solid fa-eye"></i>
                    </button>
                </td>
            `;
            tableBody.appendChild(tr);
        });

        const startIdx = currentPage * pageSize + 1;
        const endIdx = Math.min((currentPage + 1) * pageSize, total);
        updatePaginationUI(startIdx, endIdx, total, totalPages);
    }
}

function updatePaginationUI(start, end, total, totalPages = 1) {
    document.getElementById("pagination-info-text").innerText = `Showing ${start} to ${end} of ${total} entries`;
    document.getElementById("page-indicator").innerText = `Page ${currentPage + 1} of ${totalPages || 1}`;

    // Disable prev if page 0
    document.getElementById("btn-page-prev").disabled = (currentPage === 0);
    // Disable next if we reached totalPages
    document.getElementById("btn-page-next").disabled = (currentPage >= (totalPages - 1));
}

// ================= PROJECT ACTIONS =================
async function handleCreateProject(e) {
    e.preventDefault();
    const name = document.getElementById("project-name-input").value;
    const project_key = document.getElementById("project-key-input").value.trim().toUpperCase();
    const description = document.getElementById("project-desc-input").value;

    // Validate key
    if (!/^[A-Z0-9]{2,10}$/.test(project_key)) {
        alert("Project key must contain capital alphanumeric characters only (2-10 chars).");
        return;
    }

    const res = await apiRequest("/api/projects", "POST", { name, project_key, description });
    if (res.success) {
        alert("Project created successfully!");
        document.getElementById("project-create-form").reset();
        await loadProjects();
        switchView("dashboard-view");
    } else {
        alert("Project creation failed: " + res.message);
    }
}

async function renderProjectsList() {
    const container = document.getElementById("projects-list-container");
    if (projects.length === 0) {
        container.innerHTML = `<div class="empty-state"><i class="fa-solid fa-folder-minus"></i><p>No active projects. Create one on the left.</p></div>`;
        return;
    }

    container.innerHTML = "";
    projects.forEach(p => {
        const card = document.createElement("div");
        card.className = "project-card";
        card.addEventListener("click", () => {
            activeProjectId = p.id;
            localStorage.setItem("bugflow_active_project", p.id);
            syncProjectSelectors(p.id);
            switchView("dashboard-view");
        });

        card.innerHTML = `
            <div class="project-card-header">
                <h3>${escapeHTML(p.name)}</h3>
                <span class="project-card-key">${p.project_key}</span>
            </div>
            <p>${p.description ? escapeHTML(p.description) : 'No description provided.'}</p>
            <div class="detail-row" style="margin-top: 8px; font-size: 0.75rem; color: var(--text-muted);">
                <span>Created: ${new Date(p.created_at).toLocaleDateString()}</span>
            </div>
        `;
        container.appendChild(card);
    });
}

// ================= ISSUE CREATION ACTIONS =================
async function handleCreateIssueFromDashboard(e) {
    e.preventDefault();
    const projId = parseInt(document.getElementById("issue-project-select").value);
    const title = document.getElementById("issue-title-input").value;
    const description = document.getElementById("issue-desc-textarea").value;
    const issue_type = document.getElementById("issue-type-select").value;
    const priority = document.getElementById("issue-priority-select").value;
    const severity = document.getElementById("issue-severity-select").value;

    const res = await apiRequest(`/api/projects/${projId}/issues`, "POST", {
        title, description, issue_type, priority, severity
    });

    if (res.success) {
        alert(`Issue ${res.data.issue_key} created successfully!`);
        document.getElementById("dashboard-create-issue-form").reset();
        document.getElementById("duplicate-warning").style.display = "none";
        loadDashboardIssues();
    } else {
        alert("Failed to create issue: " + res.message);
    }
}

async function handleCreateIssueStandalone(e) {
    e.preventDefault();
    const projId = parseInt(document.getElementById("standalone-project-select").value);
    const title = document.getElementById("standalone-title-input").value;
    const description = document.getElementById("standalone-desc-textarea").value;
    const issue_type = document.getElementById("standalone-type-select").value;
    const priority = document.getElementById("standalone-priority-select").value;
    const severity = document.getElementById("standalone-severity-select").value;

    const res = await apiRequest(`/api/projects/${projId}/issues`, "POST", {
        title, description, issue_type, priority, severity
    });

    if (res.success) {
        alert(`Issue ${res.data.issue_key} created successfully!`);
        document.getElementById("standalone-create-issue-form").reset();
        activeProjectId = projId;
        localStorage.setItem("bugflow_active_project", projId);
        syncProjectSelectors(projId);
        switchView("issues-view");
    } else {
        alert("Failed to create issue: " + res.message);
    }
}

// ================= DUPLICATE CHECK WARNING SIMULATION =================
async function checkPotentialDuplicateTitle(e) {
    const title = e.target.value.trim().toLowerCase();
    const warningBox = document.getElementById("duplicate-warning");
    const warningText = document.getElementById("duplicate-warning-text");

    if (title.length < 5 || !activeProjectId) {
        warningBox.style.display = "none";
        return;
    }

    // Fetch latest issues to scan for duplicate
    const res = await apiRequest(`/api/projects/${activeProjectId}/issues?page=0&size=100`, "GET");
    if (res.success) {
        const issues = res.data.content;
        const duplicate = issues.find(i => i.title.toLowerCase() === title);

        if (duplicate) {
            warningText.innerHTML = `Warning: Potential duplicate of <strong>${duplicate.issue_key}</strong>: "${escapeHTML(duplicate.title)}" (100% similarity)`;
            warningBox.style.display = "flex";
        } else {
            // Check substrings
            const similar = issues.find(i => i.title.toLowerCase().includes(title) || title.includes(i.title.toLowerCase()));
            if (similar) {
                warningText.innerHTML = `Warning: Highly similar to <strong>${similar.issue_key}</strong>: "${escapeHTML(similar.title)}"`;
                warningBox.style.display = "flex";
            } else {
                warningBox.style.display = "none";
            }
        }
    }
}

// ================= MODAL ISSUE DETAIL & WORKFLOWS =================
async function openIssueDetailModal(issueId) {
    const modal = document.getElementById("issue-detail-modal");
    modal.style.display = "flex";

    // Load full issue
    const res = await apiRequest(`/api/issues/${issueId}`, "GET");
    if (res.success) {
        const issue = res.data;

        document.getElementById("modal-issue-key").innerText = issue.issue_key;
        document.getElementById("modal-issue-title").innerText = issue.title;
        document.getElementById("modal-issue-type").innerText = issue.issue_type;
        document.getElementById("modal-issue-desc").innerText = issue.description || "No description provided.";

        // Status capsule
        const statusBadge = document.getElementById("modal-status-badge");
        statusBadge.innerText = issue.status;
        statusBadge.className = `detail-value capsule capsule-${issue.status.toLowerCase().replace('_', '-')}`;

        document.getElementById("modal-priority-text").innerText = issue.priority;
        document.getElementById("modal-severity-text").innerText = issue.severity;
        document.getElementById("modal-reporter-name").innerText = issue.reporter ? issue.reporter.name : 'Unknown';
        document.getElementById("modal-created-time").innerText = new Date(issue.created_at).toLocaleString();
        document.getElementById("modal-resolved-time").innerText = issue.resolved_at ? new Date(issue.resolved_at).toLocaleString() : '-';

        // Assignee select sync
        document.getElementById("modal-assignee-select").value = issue.assignee_id || "";
        // Store current issue ID on modal form element
        modal.setAttribute("data-issue-id", issue.id);

        // Load workflow status buttons
        populateWorkflowButtons(issue);

        // Load audit logs
        loadAuditTimeline(issue.id);
    }
}

function populateWorkflowButtons(issue) {
    const container = document.getElementById("modal-workflow-buttons");
    container.innerHTML = "";

    // Status State transitions
    const validTransitions = {
        "OPEN": ["IN_PROGRESS"],
        "IN_PROGRESS": ["RESOLVED"],
        "RESOLVED": ["CLOSED", "REOPENED"],
        "CLOSED": [],
        "REOPENED": ["IN_PROGRESS"]
    };

    const allowed = validTransitions[issue.status] || [];

    // Check developer status block rule: Developers can only update status of assigned issues
    let isPermitted = true;
    if (currentUser.role === "DEVELOPER" && issue.assignee_id !== currentUser.id) {
        isPermitted = false;
    } else if (currentUser.role === "USER" && issue.reporter_id !== currentUser.id) {
        isPermitted = false;
    }

    if (allowed.length === 0) {
        container.innerHTML = '<span class="text-muted" style="font-size: 0.8rem;">Workflow complete. No further actions.</span>';
        return;
    }

    allowed.forEach(statusName => {
        const btn = document.createElement("button");
        btn.className = "btn-transition";
        btn.innerText = `Move to ${statusName.replace('_', ' ')}`;

        if (!isPermitted) {
            btn.disabled = true;
            btn.title = "You do not have privileges to move this issue's status.";
            btn.style.opacity = "0.5";
            btn.style.cursor = "not-allowed";
        } else {
            btn.addEventListener("click", () => transitionIssueStatus(issue.id, statusName));
        }

        container.appendChild(btn);
    });
}

async function transitionIssueStatus(issueId, statusName) {
    const res = await apiRequest(`/api/issues/${issueId}/status`, "PUT", { status: statusName });
    if (res.success) {
        alert("Workflow status updated!");
        await openIssueDetailModal(issueId);
        loadDashboardIssues();
        loadIssuesGrid();
    } else {
        alert("Workflow transition failed: " + res.message);
    }
}

async function handleSaveAssignment() {
    const modal = document.getElementById("issue-detail-modal");
    const issueId = modal.getAttribute("data-issue-id");
    const assigneeVal = document.getElementById("modal-assignee-select").value;
    const assigneeId = assigneeVal ? parseInt(assigneeVal) : null;

    // Check privileges
    if (currentUser.role !== "ADMIN" && currentUser.role !== "PROJECT_MANAGER") {
        alert("Only Administrators or Project Managers can assign issues.");
        return;
    }

    // Backend expects snake_case field: assignee_id
    const res = await apiRequest(`/api/issues/${issueId}/assign`, "PUT", {
        assignee_id: assigneeId
    });

    if (res.success) {
        // Refresh the modal from the backend so the selected assignee
        // reflects the persisted value rather than only the local select.
        await openIssueDetailModal(issueId);

        // Refresh both issue surfaces so the new assignee is visible
        // immediately in the Dashboard and Issues table.
        await Promise.all([
            loadDashboardIssues(),
            loadIssuesGrid()
        ]);

        alert(
            assigneeId
                ? "Assignee updated successfully!"
                : "Issue unassigned successfully!"
        );
    } else {
        alert("Failed to assign issue: " + res.message);
    }
}


async function loadAuditTimeline(issueId) {
    const container = document.getElementById("modal-issue-audit-timeline");
    container.innerHTML = "";

    const res = await apiRequest(`/api/issues/${issueId}/audit`, "GET");
    if (res.success) {
        const logs = res.data;
        if (logs.length === 0) {
            container.innerHTML = '<span class="text-muted" style="font-size: 0.8rem;">No activity log yet.</span>';
            return;
        }

        logs.forEach(l => {
            const item = document.createElement("div");
            item.className = "timeline-item";

            let changeDetail = "";
            if (l.old_value || l.new_value) {
                changeDetail = `<div class="timeline-changes">From: <em>${escapeHTML(l.old_value || 'None')}</em> → To: <em>${escapeHTML(l.new_value || 'None')}</em></div>`;
            }

            item.innerHTML = `
                <div class="timeline-meta">
                    <span class="timeline-user">${l.performed_by ? escapeHTML(l.performed_by.name) : 'System'}</span>
                    <span class="timeline-time">${new Date(l.timestamp).toLocaleString()}</span>
                </div>
                <div class="timeline-content"><strong>${l.action.replace('_', ' ')}</strong></div>
                ${changeDetail}
            `;
            container.appendChild(item);
        });
    }
}

// ================= VIEW C: INSIGHTS & REPORTS (WITH CHARTS) =================
async function loadReportsView(projectId) {
    if (!projectId) {
        document.getElementById("reports-metrics-row").style.opacity = "0.5";
        return;
    }

    document.getElementById("reports-metrics-row").style.opacity = "1";
    const res = await apiRequest(`/api/projects/${projectId}/issues/summary`, "GET");
    if (res.success) {
        const d = res.data;

        // Populate stats counters
        document.getElementById("count-total").innerText = d.totalIssues;
        document.getElementById("count-open").innerText = d.openIssues;
        document.getElementById("count-progress").innerText = d.inProgressIssues;
        document.getElementById("count-resolved").innerText = d.resolvedIssues;
        document.getElementById("count-closed").innerText = d.closedIssues;
        document.getElementById("count-critical").innerText = d.criticalIssues;

        // Render visual charts using Chart.js
        renderChartStatus(d.statusCounts);
        renderChartPriority(d.priorityCounts);
        renderChartSeverity(d.severityCounts);
        renderChartType(d.typeCounts);
    }
}

function renderChartStatus(statusCounts) {
    const ctx = document.getElementById("chart-status").getContext("2d");
    if (charts.status) charts.status.destroy();

    charts.status = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: Object.keys(statusCounts),
            datasets: [{
                data: Object.values(statusCounts),
                backgroundColor: ["#3b82f6", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6"],
                borderColor: "#161e2f",
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: "right", labels: { color: "#94a3b8" } }
            }
        }
    });
}

function renderChartPriority(priorityCounts) {
    const ctx = document.getElementById("chart-priority").getContext("2d");
    if (charts.priority) charts.priority.destroy();

    charts.priority = new Chart(ctx, {
        type: "bar",
        data: {
            labels: Object.keys(priorityCounts),
            datasets: [{
                label: "Priority Count",
                data: Object.values(priorityCounts),
                backgroundColor: "#6366f1",
                borderColor: "#818cf8",
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: { grid: { display: false }, ticks: { color: "#94a3b8" } },
                y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#94a3b8", stepSize: 1 } }
            }
        }
    });
}

function renderChartSeverity(severityCounts) {
    const ctx = document.getElementById("chart-severity").getContext("2d");
    if (charts.severity) charts.severity.destroy();

    charts.severity = new Chart(ctx, {
        type: "bar",
        data: {
            labels: Object.keys(severityCounts),
            datasets: [{
                label: "Severity Count",
                data: Object.values(severityCounts),
                backgroundColor: "#f43f5e",
                borderColor: "#fb7185",
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: { grid: { display: false }, ticks: { color: "#94a3b8" } },
                y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#94a3b8", stepSize: 1 } }
            }
        }
    });
}

function renderChartType(typeCounts) {
    const ctx = document.getElementById("chart-type").getContext("2d");
    if (charts.type) charts.type.destroy();

    charts.type = new Chart(ctx, {
        type: "polarArea",
        data: {
            labels: Object.keys(typeCounts),
            datasets: [{
                data: Object.values(typeCounts),
                backgroundColor: ["rgba(244, 63, 94, 0.6)", "rgba(6, 182, 212, 0.6)", "rgba(168, 85, 247, 0.6)", "rgba(16, 185, 129, 0.6)"],
                borderColor: "#161e2f",
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: "right", labels: { color: "#94a3b8" } }
            },
            scales: {
                r: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { display: false } }
            }
        }
    });
}

// ================= VIEW E: TEAM & ROLES LIST =================
function renderTeamList() {
    const body = document.getElementById("team-table-body");
    body.innerHTML = "";

    users.forEach(u => {
        const tr = document.createElement("tr");

        let privilegeNote = "";
        if (u.role === "ADMIN") {
            privilegeNote = `<span class="text-primary">System Overlord (All permissions)</span>`;
        } else if (u.role === "PROJECT_MANAGER") {
            privilegeNote = `Create projects, assign issues, manage workflows`;
        } else if (u.role === "DEVELOPER") {
            privilegeNote = `View all, resolve assigned issues`;
        } else if (u.role === "TESTER") {
            privilegeNote = `View all, verify & test issues`;
        } else {
            privilegeNote = `Submit bug reports, view status`;
        }

        tr.innerHTML = `
            <td><strong>${escapeHTML(u.name)}</strong></td>
            <td>${escapeHTML(u.email)}</td>
            <td><span class="badge ${u.role === 'ADMIN' ? 'badge-crit' : u.role === 'PROJECT_MANAGER' ? 'badge-high' : u.role === 'DEVELOPER' ? 'badge-med' : 'badge-low'}">${u.role}</span></td>
            <td>${privilegeNote}</td>
            <td><span style="color: var(--color-resolved);"><i class="fa-solid fa-circle" style="font-size: 0.75rem;"></i> Active</span></td>
        `;
        body.appendChild(tr);
    });
}

// ================= API UTILITIES =================
async function apiRequest(url, method = "GET", data = null) {
    const headers = {};
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }
    if (data) {
        headers["Content-Type"] = "application/json";
    }

    const options = {
        method,
        headers
    };
    if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(url, options);
        if (response.status === 401) {
            logout();
            return { success: false, message: "Session expired" };
        }
        return await response.json();
    } catch (err) {
        console.error(`API Request to ${url} failed`, err);
        return { success: false, message: "Network connection failed" };
    }
}

// JWT Token Parser
function parseJwt(token) {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(c => {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        return JSON.parse(jsonPayload);
    } catch (e) {
        return null;
    }
}

// Helper: Escape HTML strings to prevent XSS
function escapeHTML(str) {
    if (!str) return "";
    return str.replace(/[&<>'"]/g,
        tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
}

// Helper: Capitalize role name
function capitalizeRole(role) {
    if (!role) return "";
    return role.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ');
}

// Debouncer helper for search input
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
