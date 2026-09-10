// State variables
let token = localStorage.getItem("bugflow_token") || "";
let currentUser = null;
let activeProjectId = null;
let projects = [];
let users = [];
let currentPage = 0;
let pageSize = 10;

// Agile Workspace Global State
let m2Sprints = [];
let m2Issues = [];
let m2ActivityLogs = [];
let m2ActivityFilter = "ALL";
let m2PollInterval = null;
let currentModalIssue = null;

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
                    id: payload.id || null,
                    email: payload.sub,
                    role: payload.role,
                    name: payload.name
                };

                // Show Main App, hide login
                document.getElementById("auth-page").style.display = "none";
                document.getElementById("main-app").style.display = "flex";

                // Load core data
                await loadProjects();
                await loadUsers();

                if (!currentUser.id && users.length > 0) {
                    const match = users.find(u => u.email && u.email.toLowerCase() === currentUser.email.toLowerCase());
                    if (match) currentUser.id = match.id;
                }

                // Update profile cards & role views
                updateUserProfileUI();

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
            const subview = item.getAttribute("data-subview");
            switchView(viewId);
            if (subview === "sprints") {
                const el = document.getElementById("sprint-board-section");
                if (el) el.scrollIntoView({ behavior: "smooth" });
            } else if (subview === "workflow") {
                const el = document.getElementById("workflow-card-section");
                if (el) el.scrollIntoView({ behavior: "smooth" });
            }
        });
    });

    // Platform Layers Top Tabs Navigation
    const tabCore = document.getElementById("tab-core-platform");
    if (tabCore) tabCore.addEventListener("click", () => switchView("dashboard-view"));
    const tabAgile = document.getElementById("tab-agile-workspace");
    if (tabAgile) tabAgile.addEventListener("click", () => switchView("agile-workspace-view"));
    const tabCore_from_agile = document.getElementById("tab-core-from-agile");
    if (tabCore_from_agile) tabCore_from_agile.addEventListener("click", () => switchView("dashboard-view"));
    const tabAgile_from_agile = document.getElementById("tab-agile-from-agile");
    if (tabAgile_from_agile) tabAgile_from_agile.addEventListener("click", () => switchView("agile-workspace-view"));

    // Top Header Project Selector Change
    const headerProjSelect = document.getElementById("header-active-project-select");
    if (headerProjSelect) {
        headerProjSelect.addEventListener("change", (e) => {
            activeProjectId = parseInt(e.target.value);
            localStorage.setItem("bugflow_active_project", activeProjectId);
            syncProjectSelectors(activeProjectId);
            loadDashboardIssues();
            loadIssuesGrid();
        });
    }

    // Dashboard Project Selector Change (fallback if present)
    const oldProjSelect = document.getElementById("issue-project-select");
    if (oldProjSelect) {
        oldProjSelect.addEventListener("change", (e) => {
            activeProjectId = parseInt(e.target.value);
            localStorage.setItem("bugflow_active_project", activeProjectId);
            syncProjectSelectors(activeProjectId);
            loadDashboardIssues();
        });
    }

    // Agile Workspace Project Selector Change
    const m2ProjectFilter = document.getElementById("m2-project-filter");
    if (m2ProjectFilter) {
        m2ProjectFilter.addEventListener("change", (e) => {
            activeProjectId = parseInt(e.target.value);
            localStorage.setItem("bugflow_active_project", activeProjectId);
            syncProjectSelectors(activeProjectId);
            loadAgileWorkspaceView();
        });
    }

    // Agile Workspace Refresh Button
    const btnRefreshM2 = document.getElementById("btn-refresh-m2");
    if (btnRefreshM2) {
        btnRefreshM2.addEventListener("click", () => loadAgileWorkspaceView());
    }

    // Agile Workspace Workflow Search
    const workflowSearch = document.getElementById("m2-workflow-search");
    if (workflowSearch) {
        workflowSearch.addEventListener("input", debounce(renderM2WorkflowBugs, 250));
    }

    // Activity Stream Filter Chips
    document.querySelectorAll("#m2-activity-filter-bar .chip").forEach(chip => {
        chip.addEventListener("click", () => {
            document.querySelectorAll("#m2-activity-filter-bar .chip").forEach(c => c.classList.remove("active"));
            chip.classList.add("active");
            m2ActivityFilter = chip.getAttribute("data-filter");
            renderM2ActivityStream();
        });
    });

    // Create Sprint Modal triggers & actions
    const openSprintBtns = [document.getElementById("btn-open-create-sprint"), document.getElementById("btn-create-sprint-secondary")];
    openSprintBtns.forEach(btn => {
        if (btn) btn.addEventListener("click", () => {
            document.getElementById("sprint-project-select").value = activeProjectId;
            document.getElementById("create-sprint-modal").style.display = "flex";
        });
    });
    const closeSprintBtns = [document.getElementById("btn-close-sprint-modal"), document.getElementById("btn-cancel-sprint")];
    closeSprintBtns.forEach(btn => {
        if (btn) btn.addEventListener("click", () => {
            document.getElementById("create-sprint-modal").style.display = "none";
        });
    });
    const sprintForm = document.getElementById("create-sprint-form");
    if (sprintForm) sprintForm.addEventListener("submit", handleCreateSprint);

    // Executive PDF Report Modal
    const btnReport = document.getElementById("btn-generate-pdf-report");
    if (btnReport) btnReport.addEventListener("click", handleGeneratePdfReport);
    const btnCloseReport = document.getElementById("btn-close-report-modal");
    if (btnCloseReport) btnCloseReport.addEventListener("click", () => {
        document.getElementById("pdf-report-modal").style.display = "none";
    });
    const btnTriggerPrint = document.getElementById("btn-trigger-print");
    if (btnTriggerPrint) btnTriggerPrint.addEventListener("click", () => window.print());

    // Dashboard Quick Actions & Navigation
    const btnDashNew = document.getElementById("btn-dash-new-issue");
    if (btnDashNew) btnDashNew.addEventListener("click", () => switchView("report-issue-view"));
    const linkViewAll = document.getElementById("link-view-all-issues");
    if (linkViewAll) linkViewAll.addEventListener("click", (e) => { e.preventDefault(); switchView("my-issues-view"); });
    const qaReport = document.getElementById("qa-report-issue");
    if (qaReport) qaReport.addEventListener("click", () => switchView("report-issue-view"));
    const qaView = document.getElementById("qa-view-issues");
    if (qaView) qaView.addEventListener("click", () => switchView("my-issues-view"));
    const qaAssist = document.getElementById("qa-resolution-assistance");
    if (qaAssist) qaAssist.addEventListener("click", () => switchView("resolution-assistance-view"));

    // My Issues View Project Filter Selector Change
    const issuesFilterProj = document.getElementById("issues-filter-project");
    if (issuesFilterProj) {
        issuesFilterProj.addEventListener("change", (e) => {
            activeProjectId = parseInt(e.target.value);
            localStorage.setItem("bugflow_active_project", activeProjectId);
            syncProjectSelectors(activeProjectId);
            currentPage = 0;
            loadIssuesGrid();
        });
    }

    // My Issues Status Filter Pills
    document.querySelectorAll("#my-issues-status-filter .chip").forEach(chip => {
        chip.addEventListener("click", () => {
            document.querySelectorAll("#my-issues-status-filter .chip").forEach(c => c.classList.remove("active"));
            chip.classList.add("active");
            const status = chip.getAttribute("data-status");
            const statusSelect = document.getElementById("issues-filter-status");
            if (statusSelect) {
                statusSelect.value = (status === "ALL" ? "" : status);
            }
            currentPage = 0;
            loadIssuesGrid();
        });
    });

    // My Issues Scope Filter Pills (Assigned/Reported vs All)
    document.querySelectorAll("#my-issues-scope-filter .chip").forEach(chip => {
        chip.addEventListener("click", () => {
            document.querySelectorAll("#my-issues-scope-filter .chip").forEach(c => c.classList.remove("active"));
            chip.classList.add("active");
            currentPage = 0;
            loadIssuesGrid();
        });
    });

    // Issues View other filters
    const issuesFilterStatus = document.getElementById("issues-filter-status");
    if (issuesFilterStatus) {
        issuesFilterStatus.addEventListener("change", () => {
            currentPage = 0;
            loadIssuesGrid();
        });
    }
    const issuesFilterPriority = document.getElementById("issues-filter-priority");
    if (issuesFilterPriority) {
        issuesFilterPriority.addEventListener("change", () => {
            currentPage = 0;
            loadIssuesGrid();
        });
    }
    const issuesGridSearch = document.getElementById("issues-grid-search");
    if (issuesGridSearch) issuesGridSearch.addEventListener("input", debounce(loadIssuesGrid, 300));

    const dashSearch = document.getElementById("dashboard-issue-search");
    if (dashSearch) dashSearch.addEventListener("input", debounce(loadDashboardIssues, 300));

    // Dashboard Create Issue (fallback)
    const dashCreateForm = document.getElementById("dashboard-create-issue-form");
    if (dashCreateForm) dashCreateForm.addEventListener("submit", handleCreateIssueFromDashboard);

    // Standalone Create Issue Form
    const standaloneForm = document.getElementById("standalone-create-issue-form");
    if (standaloneForm) standaloneForm.addEventListener("submit", handleCreateIssueStandalone);

    // Dynamic Priority Calculation for Report Issue View
    const catSelect = document.getElementById("standalone-category-select");
    const sevSelect = document.getElementById("standalone-severity-select");
    if (catSelect && sevSelect) {
        const updateCalculatedPriority = () => {
            const cat = catSelect.value;
            const sev = sevSelect.value;
            const catWeights = {
                "Security Vulnerability": 3,
                "Database & Data Integrity": 3,
                "Backend Architecture & API": 2,
                "UI / UX & Frontend Layout": 1,
                "General Maintenance": 1
            };
            const sevWeights = {
                "CRITICAL": 4,
                "HIGH": 3,
                "MEDIUM": 2,
                "LOW": 1
            };
            const cWeight = catWeights[cat] || 2;
            const sWeight = sevWeights[sev] || 2;
            const score = cWeight * sWeight;
            let tier = "MEDIUM";
            if (score >= 12) tier = "CRITICAL";
            else if (score >= 6) tier = "HIGH";
            else if (score >= 3) tier = "MEDIUM";
            else tier = "LOW";

            const disp = document.getElementById("standalone-priority-display");
            const hiddenSelect = document.getElementById("standalone-priority-select");
            if (disp) disp.value = `${tier} (Calculated Score: ${score.toFixed(1)})`;
            if (hiddenSelect) hiddenSelect.value = tier;
        };
        window.updateStandaloneCalculatedPriority = updateCalculatedPriority;
        catSelect.addEventListener("change", updateCalculatedPriority);
        sevSelect.addEventListener("change", updateCalculatedPriority);
        updateCalculatedPriority();
    }

    // Standalone File Attachment browse button
    const btnBrowseStandalone = document.getElementById("btn-browse-standalone-file");
    const inputStandaloneAttach = document.getElementById("standalone-attachment-input");
    const labelStandaloneFilename = document.getElementById("standalone-selected-filename");
    if (btnBrowseStandalone && inputStandaloneAttach) {
        btnBrowseStandalone.addEventListener("click", () => inputStandaloneAttach.click());
        inputStandaloneAttach.addEventListener("change", () => {
            if (inputStandaloneAttach.files.length > 0) {
                labelStandaloneFilename.innerText = inputStandaloneAttach.files[0].name;
            } else {
                labelStandaloneFilename.innerText = "No file selected (.png, .jpg, .log)";
            }
        });
    }

    // Cancel Report Button
    const btnCancelReport = document.getElementById("btn-cancel-report");
    if (btnCancelReport) {
        btnCancelReport.addEventListener("click", () => switchView("dashboard-view"));
    }

    // Resolution Assistance Event Handlers
    const assistSelect = document.getElementById("assist-select-existing-issue");
    if (assistSelect) {
        assistSelect.addEventListener("change", (e) => {
            const issueId = e.target.value;
            if (issueId) loadIssueIntoAssistance(issueId);
        });
    }
    const btnRunAssist = document.getElementById("btn-run-assistance");
    if (btnRunAssist) {
        btnRunAssist.addEventListener("click", handleRunAssistanceDiagnostics);
    }

    // Project Create Form
    const projForm = document.getElementById("project-create-form");
    if (projForm) projForm.addEventListener("submit", handleCreateProject);

    // Dashboard Refresh button
    const btnRefreshDash = document.getElementById("btn-refresh-dashboard");
    if (btnRefreshDash) {
        btnRefreshDash.addEventListener("click", () => loadDashboardIssues());
    }

    // Duplicate Check Warning on Title input
    const issueTitleInput = document.getElementById("issue-title-input");
    if (issueTitleInput) issueTitleInput.addEventListener("input", checkPotentialDuplicateTitle);

    // User Simulation Switcher
    const simSelect = document.getElementById("simulated-user-select");
    if (simSelect) simSelect.addEventListener("change", handleSimulatedUserSwitch);

    // Trigger New Issue from My Issues view
    const btnNewIssueTrigger = document.getElementById("btn-new-issue-trigger");
    if (btnNewIssueTrigger) {
        btnNewIssueTrigger.addEventListener("click", () => {
            switchView("report-issue-view");
        });
    }

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

    // Modal Navigation Tabs
    document.querySelectorAll(".modal-nav-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".modal-nav-tab").forEach(t => t.classList.remove("active"));
            document.querySelectorAll(".modal-tab-pane").forEach(p => {
                p.classList.remove("active");
                p.style.display = "none";
            });
            tab.classList.add("active");
            const targetId = tab.getAttribute("data-tab");
            const targetPane = document.getElementById(targetId);
            if (targetPane) {
                targetPane.classList.add("active");
                targetPane.style.display = "block";
            }
        });
    });

    // Modal Smart Triage Trigger
    const btnRunTriage = document.getElementById("btn-run-smart-triage");
    if (btnRunTriage) btnRunTriage.addEventListener("click", handleRunSmartTriage);

    // Modal Comments Form
    const commentForm = document.getElementById("modal-add-comment-form");
    if (commentForm) commentForm.addEventListener("submit", handleAddComment);

    // Modal Attachments Actions
    const btnBrowse = document.getElementById("btn-browse-attachment");
    const fileInput = document.getElementById("modal-attachment-file-input");
    const btnUpload = document.getElementById("btn-submit-attachment");
    if (btnBrowse && fileInput) {
        btnBrowse.addEventListener("click", () => fileInput.click());
        fileInput.addEventListener("change", () => {
            if (fileInput.files.length > 0) {
                document.getElementById("modal-selected-filename").innerText = fileInput.files[0].name;
                btnUpload.disabled = false;
            } else {
                document.getElementById("modal-selected-filename").innerText = "No file chosen";
                btnUpload.disabled = true;
            }
        });
    }
    if (btnUpload) btnUpload.addEventListener("click", handleUploadAttachment);

    // Modal Assignment change save
    document.getElementById("btn-save-assignment").addEventListener("click", handleSaveAssignment);

    // Modal Edit Bug Details (Tester & Admin inline modification)
    const btnEditToggle = document.getElementById("btn-edit-issue-toggle");
    if (btnEditToggle) btnEditToggle.addEventListener("click", handleToggleIssueEdit);
    const btnCancelEdit = document.getElementById("btn-cancel-edit-issue");
    if (btnCancelEdit) {
        btnCancelEdit.addEventListener("click", () => {
            const panel = document.getElementById("modal-edit-issue-panel");
            if (panel) panel.style.display = "none";
        });
    }
    const btnSaveEdit = document.getElementById("btn-save-edit-issue");
    if (btnSaveEdit) btnSaveEdit.addEventListener("click", handleSaveIssueEdit);

    // Project Select in Reports
    const repSelect = document.getElementById("reports-project-select");
    if (repSelect) {
        repSelect.addEventListener("change", (e) => {
            const pId = parseInt(e.target.value);
            loadReportsView(pId);
        });
    }

    // Milestone 3 Event Handlers
    const btnM3Pdf = document.getElementById("btn-m3-export-pdf");
    if (btnM3Pdf) btnM3Pdf.addEventListener("click", exportPdfReport);

    const btnM3Csv = document.getElementById("btn-m3-export-csv");
    if (btnM3Csv) btnM3Csv.addEventListener("click", exportCsvReport);

    const btnM3Refresh = document.getElementById("btn-m3-refresh");
    if (btnM3Refresh) btnM3Refresh.addEventListener("click", loadMilestone3Dashboard);

    const btnSimWebhook = document.getElementById("btn-simulate-webhook");
    if (btnSimWebhook) btnSimWebhook.addEventListener("click", simulateGitWebhook);

    const btnP2 = document.getElementById("btn-preset-fixes2");
    if (btnP2) {
        btnP2.addEventListener("click", () => {
            const msgInput = document.getElementById("m3-commit-message");
            if (msgInput) msgInput.value = "Merge PR #45: fixes #2 login password crash";
        });
    }

    const btnP1 = document.getElementById("btn-preset-closes1");
    if (btnP1) {
        btnP1.addEventListener("click", () => {
            const msgInput = document.getElementById("m3-commit-message");
            if (msgInput) msgInput.value = "closes #1 sidebar overflow on laptops";
        });
    }

    const btnP3 = document.getElementById("btn-preset-resolves3");
    if (btnP3) {
        btnP3.addEventListener("click", () => {
            const msgInput = document.getElementById("m3-commit-message");
            if (msgInput) msgInput.value = "resolves #3 postgresql pool exhaustion under load";
        });
    }

    const apiPresetSel = document.getElementById("m3-api-preset-select");
    if (apiPresetSel) apiPresetSel.addEventListener("change", handleApiPresetChange);

    const btnMttrPri = document.getElementById("btn-mttr-view-priority");
    const btnMttrTtr = document.getElementById("btn-mttr-view-ttr");
    if (btnMttrPri && btnMttrTtr) {
        btnMttrPri.addEventListener("click", () => switchMttrView("priority"));
        btnMttrTtr.addEventListener("click", () => switchMttrView("ttr"));
    }

    const btnApiSend = document.getElementById("btn-m3-api-send");
    if (btnApiSend) btnApiSend.addEventListener("click", executeApiExplorerRequest);

    const btnCopyApi = document.getElementById("btn-copy-api-res");
    if (btnCopyApi) {
        btnCopyApi.addEventListener("click", () => {
            const viewer = document.getElementById("m3-api-response-viewer");
            if (viewer) {
                navigator.clipboard.writeText(viewer.innerText)
                    .then(() => alert("API response JSON copied to clipboard!"))
                    .catch(err => console.error("Could not copy text: ", err));
            }
        });
    }
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
    // Normalize aliases
    if (viewId === "issues-view") viewId = "my-issues-view";
    if (viewId === "new-issue-view") viewId = "report-issue-view";

    // Route Guard for RBAC
    const role = currentUser ? (currentUser.role || "").toUpperCase() : "";
    const restrictedRolesByView = {
        "projects-view": ["DEVELOPER", "TESTER", "USER"],
        "team-view": ["DEVELOPER", "TESTER", "USER"],
        "reports-view": ["DEVELOPER", "TESTER", "USER"],
        "agile-workspace-view": ["TESTER", "USER"],
        "resolution-assistance-view": ["USER"]
    };
    if (restrictedRolesByView[viewId] && restrictedRolesByView[viewId].includes(role)) {
        console.warn(`Access denied for role ${role} to view ${viewId}`);
        switchView("dashboard-view");
        return;
    }

    // Hide all views, activate target
    document.querySelectorAll(".app-view").forEach(view => {
        view.classList.remove("active");
    });
    const target = document.getElementById(viewId);
    if (target) target.classList.add("active");

    // Toggle active menu class in sidenav
    document.querySelectorAll(".sidebar-nav .nav-item").forEach(item => {
        item.classList.remove("active");
        if (item.getAttribute("data-view") === viewId) {
            item.classList.add("active");
        }
    });

    // Update Top Navbar Title
    const titleMap = {
        "dashboard-view": "Dashboard",
        "report-issue-view": "Report Issue",
        "my-issues-view": "My Issues",
        "resolution-assistance-view": "Resolution Assistance",
        "agile-workspace-view": "Sprints & Workflow",
        "projects-view": "Projects",
        "team-view": "Team",
        "reports-view": "Reports",
        "milestone3-view": "Analytics & APIs"
    };
    const topTitle = document.getElementById("top-navbar-title");
    if (topTitle && titleMap[viewId]) {
        topTitle.innerText = titleMap[viewId];
    }

    // Toggle Platform Layer tab active classes
    const isAgileView = (viewId === "agile-workspace-view");
    document.querySelectorAll(".platform-layer-tab").forEach(tab => {
        const layer = tab.getAttribute("data-layer");
        if (layer === "agile" && isAgileView) {
            tab.classList.add("active");
        } else if (layer === "core" && !isAgileView) {
            tab.classList.add("active");
        } else {
            tab.classList.remove("active");
        }
    });

    // Manage live activity stream polling interval
    if (isAgileView) {
        if (!m2PollInterval) {
            m2PollInterval = setInterval(fetchLiveActivityStream, 10000);
        }
    } else {
        if (m2PollInterval) {
            clearInterval(m2PollInterval);
            m2PollInterval = null;
        }
    }

    // View specific initial loads
    if (viewId === "dashboard-view") {
        loadDashboardIssues();
    } else if (viewId === "my-issues-view") {
        loadIssuesGrid();
    } else if (viewId === "report-issue-view") {
        syncProjectSelectors(activeProjectId);
        if (typeof window.updateStandaloneCalculatedPriority === "function") {
            window.updateStandaloneCalculatedPriority();
        }
    } else if (viewId === "resolution-assistance-view") {
        populateAssistExistingIssues();
    } else if (viewId === "projects-view") {
        renderProjectsList();
    } else if (viewId === "reports-view") {
        loadReportsView(activeProjectId);
    } else if (viewId === "team-view") {
        renderTeamList();
    } else if (viewId === "agile-workspace-view") {
        loadAgileWorkspaceView();
    } else if (viewId === "milestone3-view") {
        loadMilestone3Dashboard();
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
    const sbName = document.getElementById("sidebar-name");
    if (sbName) sbName.innerText = currentUser.name;
    const sbRole = document.getElementById("sidebar-role");
    if (sbRole) sbRole.innerText = capitalizeRole(currentUser.role);
    const sbAvatar = document.getElementById("sidebar-avatar");
    if (sbAvatar) {
        const initials = currentUser.name.split(" ").map(n => n[0]).join("").substring(0, 2).toUpperCase();
        sbAvatar.innerText = initials;
    }

    // Top Navbar Profile Pill (Image 1 / Image 2 style)
    const navUsername = document.getElementById("navbar-username");
    if (navUsername) navUsername.innerText = currentUser.name;
    const navRole = document.getElementById("navbar-role");
    if (navRole) navRole.innerText = (currentUser.role || "USER").toUpperCase();
    const navAvatar = document.getElementById("navbar-avatar");
    if (navAvatar) {
        const firstLetter = (currentUser.name && currentUser.name.length > 0) ? currentUser.name[0].toUpperCase() : "U";
        navAvatar.innerText = firstLetter;
    }

    // Dashboard Welcome Banner
    const dashName = document.getElementById("dash-user-name");
    if (dashName) dashName.innerText = currentUser.name;

    // Header simulated status configuration (if present)
    const authBadge = document.getElementById("header-auth-badge");
    if (authBadge) {
        authBadge.innerText = `Auth: Role-based configured for ${currentUser.role} (${currentUser.name})`;
    }

    const role = (currentUser.role || "USER").toUpperCase();

    // 1. Role Simulator: ONLY ADMINs can see role switcher; hidden for normal roles
    const simContainer = document.getElementById("role-simulator-container");
    if (simContainer) {
        simContainer.style.display = (role === "ADMIN") ? "block" : "none";
    }

    // 2. Sidebar Navigation Items by Role
    const navProjects = document.getElementById("nav-projects");
    const navTeam = document.getElementById("nav-team");
    const navReports = document.getElementById("nav-reports");
    const navAgile = document.getElementById("nav-agile-workspace");
    const navAssist = document.getElementById("nav-resolution-assistance");
    const navMyIssues = document.getElementById("nav-my-issues");

    if (navMyIssues) {
        if (role === "DEVELOPER") {
            navMyIssues.innerHTML = '<i class="fa-solid fa-list-check"></i> Assigned Issues';
        } else if (role === "TESTER") {
            navMyIssues.innerHTML = '<i class="fa-solid fa-list-check"></i> My Reported Issues';
        } else {
            navMyIssues.innerHTML = '<i class="fa-solid fa-list-check"></i> My Issues';
        }
    }

    if (role === "DEVELOPER") {
        if (navProjects) navProjects.style.display = "none";
        if (navTeam) navTeam.style.display = "none";
        if (navReports) navReports.style.display = "none";
        if (navAgile) navAgile.style.display = "flex";
        if (navAssist) navAssist.style.display = "flex";
    } else if (role === "TESTER") {
        if (navProjects) navProjects.style.display = "none";
        if (navTeam) navTeam.style.display = "none";
        if (navReports) navReports.style.display = "none";
        if (navAgile) navAgile.style.display = "none";
        if (navAssist) navAssist.style.display = "flex";
    } else if (role === "USER") {
        if (navProjects) navProjects.style.display = "none";
        if (navTeam) navTeam.style.display = "none";
        if (navReports) navReports.style.display = "none";
        if (navAgile) navAgile.style.display = "none";
        if (navAssist) navAssist.style.display = "none";
    } else {
        // ADMIN & PROJECT_MANAGER
        if (navProjects) navProjects.style.display = "flex";
        if (navTeam) navTeam.style.display = "flex";
        if (navReports) navReports.style.display = "flex";
        if (navAgile) navAgile.style.display = "flex";
        if (navAssist) navAssist.style.display = "flex";
    }

    // 3. Dashboard Banner and Recent Issues Titles based on Role
    const dashBannerSub = document.querySelector(".dash-welcome-text p");
    const dashRecentHeader = document.querySelector(".recent-issues-card .dash-card-header h2");
    const dashRecentSubtitle = document.querySelector(".recent-issues-card .dash-card-subtitle");

    if (role === "DEVELOPER") {
        if (dashBannerSub) dashBannerSub.innerText = "Here's an overview of your assigned issues and their current status.";
        if (dashRecentHeader) dashRecentHeader.innerText = "My Assigned Issues";
        if (dashRecentSubtitle) dashRecentSubtitle.innerText = "Latest issues assigned to you";
    } else if (role === "TESTER" || role === "USER") {
        if (dashBannerSub) dashBannerSub.innerText = "Here's an overview of your reported issues and their current status.";
        if (dashRecentHeader) dashRecentHeader.innerText = "My Reported Issues";
        if (dashRecentSubtitle) dashRecentSubtitle.innerText = "Latest issues reported by you";
    } else {
        if (dashBannerSub) dashBannerSub.innerText = "Here's an overview of project issues and team velocity.";
        if (dashRecentHeader) dashRecentHeader.innerText = "Recent Issues";
        if (dashRecentSubtitle) dashRecentSubtitle.innerText = "Latest issues across the active project";
    }

    // 4. My Issues View Header & Scope Filter Configuration
    const myIssuesTitle = document.querySelector("#my-issues-view .page-title-banner h1");
    const myIssuesDesc = document.querySelector("#my-issues-view .page-title-banner p");
    const scopeFilter = document.getElementById("my-issues-scope-filter");
    const chipScopePrimary = document.getElementById("chip-scope-primary");

    if (role === "DEVELOPER") {
        if (myIssuesTitle) myIssuesTitle.innerText = "Assigned Issues";
        if (myIssuesDesc) myIssuesDesc.innerText = "Track all issues assigned to your account.";
        if (chipScopePrimary) chipScopePrimary.innerText = "My Assigned";
        if (scopeFilter) scopeFilter.style.display = "flex";
    } else if (role === "TESTER") {
        if (myIssuesTitle) myIssuesTitle.innerText = "My Reported Issues";
        if (myIssuesDesc) myIssuesDesc.innerText = "Track all issues reported by your account.";
        if (chipScopePrimary) chipScopePrimary.innerText = "My Reported";
        if (scopeFilter) scopeFilter.style.display = "flex";
    } else if (role === "USER") {
        if (myIssuesTitle) myIssuesTitle.innerText = "My Reported Issues";
        if (myIssuesDesc) myIssuesDesc.innerText = "Track all issues reported by your account.";
        if (chipScopePrimary) chipScopePrimary.innerText = "My Reported";
        if (scopeFilter) scopeFilter.style.display = "none";
    } else {
        if (myIssuesTitle) myIssuesTitle.innerText = "Project Issues";
        if (myIssuesDesc) myIssuesDesc.innerText = "Manage and track all issues in the project.";
        if (chipScopePrimary) chipScopePrimary.innerText = "My Items";
        if (scopeFilter) scopeFilter.style.display = "flex";
    }
}

function populateProjectSelectors() {
    const selectors = [
        "header-active-project-select",
        "issue-project-select",
        "issues-filter-project",
        "standalone-project-select",
        "reports-project-select",
        "m2-project-filter",
        "sprint-project-select"
    ];
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
    const selectors = ["modal-assignee-select", "standalone-assignee-select"];
    selectors.forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        el.innerHTML = (id === "standalone-assignee-select")
            ? '<option value="">Leave Unassigned (Pending Triage)</option>'
            : '<option value="">Unassigned</option>';

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
    const selectors = [
        "header-active-project-select",
        "issue-project-select",
        "issues-filter-project",
        "standalone-project-select",
        "reports-project-select",
        "m2-project-filter",
        "sprint-project-select"
    ];
    selectors.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = projectId;
    });
}

// ================= VIEW A: DASHBOARD ISSUES (IMAGE 1 STYLE) =================
async function loadDashboardIssues() {
    const tableBody = document.getElementById("dash-recent-issues-tbody");
    if (!activeProjectId) {
        if (tableBody) tableBody.innerHTML = `<tr><td colspan="4" class="empty-state" style="text-align: center; padding: 24px; color: var(--text-muted);">No project selected. Create or select a project.</td></tr>`;
        return;
    }

    let url = `/api/projects/${activeProjectId}/issues?page=0&size=50`;
    if (currentUser && currentUser.id) {
        if (currentUser.role === "DEVELOPER") {
            url += `&assignee=${currentUser.id}`;
        } else if (currentUser.role === "TESTER" || currentUser.role === "USER") {
            url += `&reporter=${currentUser.id}`;
        }
    }

    const res = await apiRequest(url, "GET");
    if (res.success) {
        const issues = res.data.content || [];
        const total = res.data.totalElements || issues.length;

        // Stat metrics calculation
        const openCount = issues.filter(i => ["OPEN", "REPORTED", "TRIAGED"].includes(i.status)).length;
        const progressCount = issues.filter(i => ["IN_PROGRESS", "QA_VERIFICATION"].includes(i.status)).length;
        const resolvedCount = issues.filter(i => ["RESOLVED", "CLOSED"].includes(i.status)).length;

        const statTotal = document.getElementById("dash-stat-total");
        const statOpen = document.getElementById("dash-stat-open");
        const statProgress = document.getElementById("dash-stat-progress");
        const statResolved = document.getElementById("dash-stat-resolved");

        if (statTotal) statTotal.innerText = total;
        if (statOpen) statOpen.innerText = openCount;
        if (statProgress) statProgress.innerText = progressCount;
        if (statResolved) statResolved.innerText = resolvedCount;

        // Render My Recent Issues table
        if (!tableBody) return;
        if (issues.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="4" class="empty-state" style="text-align: center; padding: 24px; color: var(--text-muted);"><i class="fa-solid fa-folder-open"></i><p>No recent issues found in this project.</p></td></tr>`;
            return;
        }

        tableBody.innerHTML = "";
        // Show up to 6 recent issues
        const recent = issues.slice(0, 6);
        recent.forEach(i => {
            const tr = document.createElement("tr");
            tr.style.cursor = "pointer";
            tr.addEventListener("click", () => openIssueDetailModal(i.id));

            const priorityBadge = `badge-${i.priority.toLowerCase() === 'critical' ? 'crit' : i.priority.toLowerCase() === 'high' ? 'high' : i.priority.toLowerCase() === 'medium' ? 'med' : 'low'}`;

            const issueKeyFormatted = i.issue_key ? (i.issue_key.startsWith('#') ? i.issue_key : '#' + i.issue_key) : `#${i.id}`;
            tr.innerHTML = `
                <td class="cell-key"><span class="table-issue-key font-bold" style="color: #6366f1;">${issueKeyFormatted}</span></td>
                <td class="cell-title font-medium">${escapeHTML(i.title)}</td>
                <td><span class="badge ${priorityBadge}">${i.priority}</span></td>
                <td><span class="capsule capsule-${i.status.toLowerCase().replace('_', '-')}">${formatStatus(i.status)}</span></td>
            `;
            tableBody.appendChild(tr);
        });
    }
}


// ================= VIEW B: ISSUES GRID TABLE (IMAGE 2 STYLE) =================
async function loadIssuesGrid() {
    const tableBody = document.getElementById("issues-table-body");
    if (!tableBody) return;
    if (!activeProjectId) {
        tableBody.innerHTML = `<tr><td colspan="9" class="empty-state"><i class="fa-solid fa-folder"></i><p>Select a project</p></td></tr>`;
        return;
    }

    const statusVal = document.getElementById("issues-filter-status") ? document.getElementById("issues-filter-status").value : "";
    const priorityVal = document.getElementById("issues-filter-priority") ? document.getElementById("issues-filter-priority").value : "";
    const searchVal = document.getElementById("issues-grid-search") ? document.getElementById("issues-grid-search").value : "";

    const activeScopeChip = document.querySelector("#my-issues-scope-filter .chip.active");
    const scope = activeScopeChip ? activeScopeChip.getAttribute("data-scope") : "mine";

    let url = `/api/projects/${activeProjectId}/issues?page=${currentPage}&size=${pageSize}`;
    if (statusVal) url += `&status=${statusVal}`;
    if (priorityVal) url += `&priority=${priorityVal}`;

    if (scope === "mine" && currentUser && currentUser.id) {
        if (currentUser.role === "DEVELOPER") {
            url += `&assignee=${currentUser.id}`;
        } else if (currentUser.role === "TESTER" || currentUser.role === "USER") {
            url += `&reporter=${currentUser.id}`;
        }
    }

    const res = await apiRequest(url, "GET");
    if (res.success) {
        let issues = res.data.content || [];
        const total = res.data.totalElements || issues.length;
        const totalPages = res.data.totalPages || 1;

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
            tr.style.cursor = "pointer";
            tr.addEventListener("click", () => openIssueDetailModal(i.id));

            const severityBadge = `badge-${i.severity.toLowerCase() === 'critical' ? 'crit' : i.severity.toLowerCase() === 'high' ? 'high' : i.severity.toLowerCase() === 'medium' ? 'med' : 'low'}`;
            const priorityBadge = `badge-${i.priority.toLowerCase() === 'critical' ? 'crit' : i.priority.toLowerCase() === 'high' ? 'high' : i.priority.toLowerCase() === 'medium' ? 'med' : 'low'}`;

            tr.innerHTML = `
                <td class="cell-key"><span class="table-issue-key font-bold" style="color: #6366f1;">${i.issue_key}</span></td>
                <td class="cell-title font-medium">${escapeHTML(i.title)}</td>
                <td>${i.issue_type}</td>
                <td><span class="badge ${severityBadge}">${i.severity}</span></td>
                <td><span class="badge ${priorityBadge}">${i.priority}</span></td>
                <td><span class="capsule capsule-${i.status.toLowerCase().replace('_', '-')}">${formatStatus(i.status)}</span></td>
                <td>${i.reporter ? escapeHTML(i.reporter.name) : 'Unknown'}</td>
                <td>${i.assignee ? escapeHTML(i.assignee.name) : '<span class="text-muted">Unassigned</span>'}</td>
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
    const info = document.getElementById("pagination-info-text");
    const indicator = document.getElementById("page-indicator");
    const btnPrev = document.getElementById("btn-page-prev");
    const btnNext = document.getElementById("btn-page-next");

    if (info) info.innerText = `Showing ${start} to ${end} of ${total} entries`;
    if (indicator) indicator.innerText = `Page ${currentPage + 1} of ${totalPages || 1}`;

    // Disable prev if page 0
    if (btnPrev) btnPrev.disabled = (currentPage === 0);
    // Disable next if we reached totalPages
    if (btnNext) btnNext.disabled = (currentPage >= (totalPages - 1));
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
    if (!container) return;
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
    const projSelect = document.getElementById("issue-project-select") || document.getElementById("header-active-project-select");
    const projId = projSelect ? parseInt(projSelect.value) : activeProjectId;
    const titleInput = document.getElementById("issue-title-input");
    const title = titleInput ? titleInput.value : "";
    const description = document.getElementById("issue-desc-textarea")?.value || "";
    const issue_type = document.getElementById("issue-type-select")?.value || "BUG";
    const priority = document.getElementById("issue-priority-select")?.value || "MEDIUM";
    const severity = document.getElementById("issue-severity-select")?.value || "MEDIUM";

    if (!projId) {
        alert("Please select a project.");
        return;
    }

    const res = await apiRequest(`/api/projects/${projId}/issues`, "POST", {
        title, description, issue_type, priority, severity
    });

    if (res.success) {
        alert(`Issue ${res.data.issue_key} created successfully!`);
        const form = document.getElementById("dashboard-create-issue-form");
        if (form) form.reset();
        const warn = document.getElementById("duplicate-warning");
        if (warn) warn.style.display = "none";
        loadDashboardIssues();
    } else {
        alert("Failed to create issue: " + res.message);
    }
}

async function handleCreateIssueStandalone(e) {
    e.preventDefault();
    const projId = parseInt(document.getElementById("standalone-project-select").value);
    const title = document.getElementById("standalone-title-input").value.trim();
    const category = document.getElementById("standalone-category-select").value;
    const issue_type = document.getElementById("standalone-type-select").value;
    const priority = document.getElementById("standalone-priority-select").value || "MEDIUM";
    const severity = document.getElementById("standalone-severity-select").value;
    const env = (document.getElementById("standalone-env-input")?.value || "").trim();
    const moduleName = (document.getElementById("standalone-module-input")?.value || "").trim();
    const steps = (document.getElementById("standalone-steps-textarea")?.value || "").trim();
    const desc = document.getElementById("standalone-desc-textarea").value.trim();
    const assigneeVal = document.getElementById("standalone-assignee-select") ? document.getElementById("standalone-assignee-select").value : "";
    const assignee_id = assigneeVal ? parseInt(assigneeVal) : null;

    if (!projId) {
        alert("Please select a project.");
        return;
    }

    let fullDescription = "";
    if (steps) {
        fullDescription += `### Steps to Reproduce:\n${steps}\n\n`;
    }
    if (desc) {
        fullDescription += `### Description & Expected vs Actual Result:\n${desc}\n\n`;
    }
    if (env || moduleName) {
        fullDescription += `--- Technical Details ---`;
        if (env) fullDescription += `\nEnvironment: ${env}`;
        if (moduleName) fullDescription += `\nAffected Module: ${moduleName}`;
    }
    fullDescription = fullDescription.trim();

    const submitBtn = document.getElementById("btn-submit-report");
    const origBtnText = submitBtn ? submitBtn.innerHTML : "";
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Submitting...`;
    }

    try {
        const res = await apiRequest(`/api/projects/${projId}/issues`, "POST", {
            title,
            description: fullDescription,
            issue_type,
            priority,
            severity,
            category,
            assignee_id
        });

        if (res.success) {
            const newIssue = res.data;

            // Handle optional file attachment
            const fileInput = document.getElementById("standalone-attachment-input");
            if (fileInput && fileInput.files && fileInput.files.length > 0) {
                const formData = new FormData();
                formData.append("file", fileInput.files[0]);
                try {
                    await fetch(`/api/v1/issues/${newIssue.id}/attachments`, {
                        method: "POST",
                        headers: { "Authorization": `Bearer ${token}` },
                        body: formData
                    });
                } catch (attErr) {
                    console.error("Attachment upload error", attErr);
                }
            }

            alert(`Issue ${newIssue.issue_key} reported successfully!`);
            document.getElementById("standalone-create-issue-form").reset();
            const labelFile = document.getElementById("standalone-selected-filename");
            if (labelFile) labelFile.innerText = "No file selected (.png, .jpg, .log)";

            // Re-run priority calculation for reset form defaults
            if (typeof window.updateStandaloneCalculatedPriority === "function") {
                window.updateStandaloneCalculatedPriority();
            }

            activeProjectId = projId;
            localStorage.setItem("bugflow_active_project", projId);
            syncProjectSelectors(projId);

            // Switch to My Issues view
            switchView("my-issues-view");
        } else {
            alert("Failed to create issue: " + res.message);
        }
    } catch (err) {
        console.error(err);
        alert("An error occurred while creating the issue.");
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = origBtnText;
        }
    }
}

// ================= RESOLUTION ASSISTANCE & SMART TRIAGE =================
async function populateAssistExistingIssues() {
    const select = document.getElementById("assist-select-existing-issue");
    if (!select || !activeProjectId) return;

    const res = await apiRequest(`/api/projects/${activeProjectId}/issues?page=0&size=100`, "GET");
    if (res.success) {
        const issues = res.data.content || [];
        select.innerHTML = '<option value="">-- Choose an issue to diagnose --</option>';
        issues.forEach(i => {
            const opt = document.createElement("option");
            opt.value = i.id;
            opt.innerText = `${i.issue_key} - ${i.title}`;
            select.appendChild(opt);
        });
    }
}

async function loadIssueIntoAssistance(issueId) {
    const res = await apiRequest(`/api/issues/${issueId}`, "GET");
    if (res.success) {
        const issue = res.data;
        const titleInput = document.getElementById("assist-issue-title");
        const descInput = document.getElementById("assist-issue-desc");
        const sevSelect = document.getElementById("assist-issue-severity");
        const catSelect = document.getElementById("assist-issue-category");

        if (titleInput) titleInput.value = issue.title;
        if (descInput) descInput.value = issue.description || "";
        if (sevSelect && issue.severity) sevSelect.value = issue.severity;
        if (catSelect && issue.category) catSelect.value = issue.category;
    }
}

async function handleRunAssistanceDiagnostics() {
    const titleInput = document.getElementById("assist-issue-title");
    const descInput = document.getElementById("assist-issue-desc");
    const sevSelect = document.getElementById("assist-issue-severity");
    const catSelect = document.getElementById("assist-issue-category");

    const title = titleInput ? titleInput.value.trim() : "";
    const description = descInput ? descInput.value.trim() : "";
    const severity = sevSelect ? sevSelect.value : "MEDIUM";
    const category = catSelect ? catSelect.value : "Backend Architecture & API";

    if (!title) {
        alert("Please enter or select an issue title to diagnose.");
        return;
    }

    const btn = document.getElementById("btn-run-assistance");
    const origText = btn ? btn.innerHTML : "";
    if (btn) {
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Calculating Priority & Matching Experts...`;
        btn.disabled = true;
    }

    try {
        const res = await apiRequest("/api/v1/issues/triage-recommendation", "POST", {
            title,
            description,
            severity,
            category
        });

        if (res.success) {
            renderAssistanceResults(res.data);
        } else {
            alert("Diagnostics failed: " + res.message);
        }
    } catch (err) {
        console.error(err);
        alert("Error running assistance diagnostics.");
    } finally {
        if (btn) {
            btn.innerHTML = origText;
            btn.disabled = false;
        }
    }
}

function renderAssistanceResults(data) {
    const banner = document.getElementById("assist-score-banner");
    const scoreVal = document.getElementById("assist-score-value");
    const tierBadge = document.getElementById("assist-tier-badge");
    const formulaText = document.getElementById("assist-formula-text");
    const matchesList = document.getElementById("assist-dev-matches-list");

    if (banner) banner.style.display = "flex";
    if (scoreVal) scoreVal.innerText = (data.priority_score !== undefined) ? data.priority_score.toFixed(1) : "-";
    if (tierBadge) {
        tierBadge.innerText = data.recommended_priority || "MEDIUM";
        const tierLower = (data.recommended_priority || "medium").toLowerCase();
        tierBadge.className = `badge badge-${tierLower === 'critical' ? 'crit' : tierLower === 'high' ? 'high' : tierLower === 'medium' ? 'med' : 'low'}`;
    }
    if (formulaText) {
        formulaText.innerText = data.formula || `Severity (${data.severity_weight}) × Category (${data.category_urgency_weight}) = ${data.priority_score}`;
    }

    if (matchesList) {
        if (!data.recommended_developers || data.recommended_developers.length === 0) {
            matchesList.innerHTML = `<p class="text-secondary" style="font-size: 0.85rem; padding: 10px;">No developer recommendations found for this issue's skillset.</p>`;
            return;
        }

        matchesList.innerHTML = "";
        data.recommended_developers.forEach(dev => {
            const devCard = document.createElement("div");
            devCard.className = "dev-match-card";
            devCard.innerHTML = `
                <div class="dev-match-header">
                    <div class="dev-match-name-group">
                        <div class="dev-avatar-sm">${dev.name.charAt(0).toUpperCase()}</div>
                        <div>
                            <strong class="dev-name">${escapeHTML(dev.name)}</strong>
                            <span class="dev-tasks-badge">${dev.active_tasks} active task${dev.active_tasks === 1 ? '' : 's'}</span>
                        </div>
                    </div>
                    <span class="match-percentage-badge">${dev.match_percentage}% Match</span>
                </div>
                <p class="dev-skills-text"><i class="fa-solid fa-code"></i> Skills: <span>${escapeHTML(dev.skills || 'None')}</span></p>
                <p class="dev-rationale-text"><i class="fa-solid fa-circle-info"></i> ${escapeHTML(dev.rationale || '')}</p>
            `;
            matchesList.appendChild(devCard);
        });
    }
}

// Status Formatting Helper
function formatStatus(status) {
    if (!status) return "";
    const map = {
        "OPEN": "Open",
        "REPORTED": "Reported",
        "TRIAGED": "Triaged",
        "IN_PROGRESS": "In Progress",
        "QA_VERIFICATION": "QA Verification",
        "RESOLVED": "Resolved",
        "CLOSED": "Closed",
        "REOPENED": "Reopened"
    };
    return map[status] || status;
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
async function openIssueDetailModal(issueId, defaultTab = "tab-overview") {
    const modal = document.getElementById("issue-detail-modal");
    modal.style.display = "flex";

    // Switch to target modal tab
    document.querySelectorAll(".modal-nav-tab").forEach(tab => {
        if (tab.getAttribute("data-tab") === defaultTab) {
            tab.classList.add("active");
        } else {
            tab.classList.remove("active");
        }
    });
    document.querySelectorAll(".modal-tab-pane").forEach(pane => {
        if (pane.id === defaultTab) {
            pane.classList.add("active");
            pane.style.display = "block";
        } else {
            pane.classList.remove("active");
            pane.style.display = "none";
        }
    });

    // Reset smart triage results
    const triageBox = document.getElementById("modal-triage-results");
    if (triageBox) triageBox.style.display = "none";

    // Load full issue
    const res = await apiRequest(`/api/issues/${issueId}`, "GET");
    if (res.success) {
        const issue = res.data;
        currentModalIssue = issue;

        document.getElementById("modal-issue-key").innerText = issue.issue_key;
        document.getElementById("modal-issue-title").innerText = issue.title;
        document.getElementById("modal-issue-type").innerText = issue.issue_type;

        // Extract Steps to Reproduce and Description
        const rawDesc = issue.description || "";
        let stepsText = "";
        let mainDescText = rawDesc;

        const stepsMatch = rawDesc.match(/(?:###\s*Steps to Reproduce:|Steps to Reproduce:)\s*([\s\S]*?)(?=(?:###\s*Description|Description & Expected|--- Technical Details ---|$))/i);
        if (stepsMatch && stepsMatch[1]) {
            stepsText = stepsMatch[1].trim();
        }

        const descMatch = rawDesc.match(/(?:###\s*Description & Expected vs Actual Result:|###\s*Description & Expected vs Actual:|Description & Expected vs Actual:)\s*([\s\S]*?)(?=(?:--- Technical Details ---|$))/i);
        if (descMatch && descMatch[1]) {
            mainDescText = descMatch[1].trim();
        } else if (stepsMatch) {
            mainDescText = rawDesc.replace(/(?:###\s*Steps to Reproduce:|Steps to Reproduce:)[\s\S]*?(?=(?:###\s*Description|Description & Expected|--- Technical Details ---|$))/i, "").trim();
            mainDescText = mainDescText.replace(/^###\s*Description & Expected vs Actual Result:\s*/i, "").trim();
            mainDescText = mainDescText.replace(/^###\s*Description & Expected vs Actual:\s*/i, "").trim();
        }

        const stepsContainer = document.getElementById("modal-section-steps");
        const stepsBox = document.getElementById("modal-issue-steps");
        if (stepsContainer && stepsBox) {
            if (stepsText) {
                stepsBox.innerText = stepsText;
                stepsContainer.style.display = "block";
            } else {
                stepsBox.innerHTML = `<em class="text-muted">No explicit steps to reproduce recorded.</em>`;
                stepsContainer.style.display = "block";
            }
        }

        const descBox = document.getElementById("modal-issue-desc");
        if (descBox) {
            descBox.innerText = mainDescText || "No description provided.";
        }

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

        // Configure Edit Bug button visibility (Admin, PM, or Tester/User who reported this bug)
        const btnEditToggle = document.getElementById("btn-edit-issue-toggle");
        const editPanel = document.getElementById("modal-edit-issue-panel");
        if (editPanel) editPanel.style.display = "none";

        let canEdit = false;
        if (currentUser.role === "ADMIN" || currentUser.role === "PROJECT_MANAGER") {
            canEdit = true;
        } else if ((currentUser.role === "TESTER" || currentUser.role === "USER") && issue.reporter_id === currentUser.id) {
            canEdit = true;
        }

        if (btnEditToggle) {
            btnEditToggle.style.display = canEdit ? "inline-flex" : "none";
        }

        // Configure Assign Owner Panel Permissions
        const assignSelect = document.getElementById("modal-assignee-select");
        const assignBtn = document.getElementById("btn-save-assignment");
        if (assignSelect && assignBtn) {
            let allowAssignUI = false;
            if (currentUser.role === "ADMIN" || currentUser.role === "PROJECT_MANAGER") {
                allowAssignUI = true;
            } else if (currentUser.role === "TESTER" && issue.reporter_id === currentUser.id) {
                allowAssignUI = true;
            } else if (currentUser.role === "DEVELOPER" && (issue.assignee_id === currentUser.id || !issue.assignee_id)) {
                allowAssignUI = true;
            }

            assignSelect.disabled = !allowAssignUI;
            assignBtn.disabled = !allowAssignUI;
            assignBtn.style.display = allowAssignUI ? "inline-flex" : "none";
        }

        // Load workflow status buttons
        populateWorkflowButtons(issue);

        // Load audit logs
        loadAuditTimeline(issue.id);

        // Agile tabs: Load comments & attachments
        loadModalComments(issue.id);
        loadModalAttachments(issue.id);
    }
}

function populateWorkflowButtons(issue) {
    const container = document.getElementById("modal-workflow-buttons");
    container.innerHTML = "";

    // Status State transitions (supports linear agile workflow state machine)
    const validTransitions = {
        "REPORTED": ["TRIAGED", "CLOSED"],
        "TRIAGED": ["IN_PROGRESS", "CLOSED"],
        "OPEN": ["TRIAGED", "IN_PROGRESS", "CLOSED"],
        "IN_PROGRESS": ["QA_VERIFICATION", "RESOLVED"],
        "QA_VERIFICATION": ["RESOLVED", "IN_PROGRESS"],
        "RESOLVED": ["CLOSED", "REOPENED"],
        "CLOSED": ["REOPENED"],
        "REOPENED": ["IN_PROGRESS", "TRIAGED"]
    };

    const allowed = validTransitions[issue.status] || [];

    // Check status transition permissions:
    // DEVELOPER can update status of assigned issues
    // TESTER can update status of their reported issues
    // USER can update status of their reported issues
    // ADMIN & PROJECT_MANAGER can update any issue
    let isPermitted = true;
    if (currentUser.role === "DEVELOPER" && issue.assignee_id !== currentUser.id) {
        isPermitted = false;
    } else if ((currentUser.role === "TESTER" || currentUser.role === "USER") && issue.reporter_id !== currentUser.id) {
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

    // Check privileges:
    // ADMIN, PROJECT_MANAGER: can assign any issue
    // TESTER: can assign issues they reported
    // DEVELOPER: can self-assign or reassign issues assigned to them
    const issue = currentModalIssue;
    let canAssign = false;
    if (currentUser.role === "ADMIN" || currentUser.role === "PROJECT_MANAGER") {
        canAssign = true;
    } else if (currentUser.role === "TESTER" && issue && issue.reporter_id === currentUser.id) {
        canAssign = true;
    } else if (currentUser.role === "DEVELOPER" && issue && (issue.assignee_id === currentUser.id || assigneeId === currentUser.id)) {
        canAssign = true;
    }

    if (!canAssign) {
        if (currentUser.role === "TESTER") {
            alert("Testers can only assign issues they reported.");
        } else if (currentUser.role === "DEVELOPER") {
            alert("Developers can only self-assign or reassign their assigned issues.");
        } else {
            alert("You do not have permission to assign this issue.");
        }
        return;
    }

    // Backend expects snake_case field: assignee_id
    const res = await apiRequest(`/api/issues/${issueId}/assign`, "PUT", {
        assignee_id: assigneeId
    });

    if (res.success) {
        await openIssueDetailModal(issueId);
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

function handleToggleIssueEdit() {
    if (!currentModalIssue) return;
    const editPanel = document.getElementById("modal-edit-issue-panel");
    if (!editPanel) return;

    if (editPanel.style.display === "none" || !editPanel.style.display) {
        // Prefill inputs
        const titleInput = document.getElementById("modal-edit-title");
        const sevSelect = document.getElementById("modal-edit-severity");
        const catSelect = document.getElementById("modal-edit-category");
        const stepsArea = document.getElementById("modal-edit-steps");
        const descArea = document.getElementById("modal-edit-desc");

        if (titleInput) titleInput.value = currentModalIssue.title || "";
        if (sevSelect) sevSelect.value = currentModalIssue.severity || "MEDIUM";
        if (catSelect) catSelect.value = currentModalIssue.category || "Backend Architecture & API";

        const rawDesc = currentModalIssue.description || "";
        let stepsText = "";
        let mainDescText = rawDesc;

        const stepsMatch = rawDesc.match(/(?:###\s*Steps to Reproduce:|Steps to Reproduce:)\s*([\s\S]*?)(?=(?:###\s*Description|Description & Expected|--- Technical Details ---|$))/i);
        if (stepsMatch && stepsMatch[1]) {
            stepsText = stepsMatch[1].trim();
        }

        const descMatch = rawDesc.match(/(?:###\s*Description & Expected vs Actual Result:|###\s*Description & Expected vs Actual:|Description & Expected vs Actual:)\s*([\s\S]*?)(?=(?:--- Technical Details ---|$))/i);
        if (descMatch && descMatch[1]) {
            mainDescText = descMatch[1].trim();
        } else if (stepsMatch) {
            mainDescText = rawDesc.replace(/(?:###\s*Steps to Reproduce:|Steps to Reproduce:)[\s\S]*?(?=(?:###\s*Description|Description & Expected|--- Technical Details ---|$))/i, "").trim();
            mainDescText = mainDescText.replace(/^###\s*Description & Expected vs Actual Result:\s*/i, "").trim();
        }

        if (stepsArea) stepsArea.value = stepsText;
        if (descArea) descArea.value = mainDescText;

        editPanel.style.display = "block";
        editPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } else {
        editPanel.style.display = "none";
    }
}

async function handleSaveIssueEdit() {
    if (!currentModalIssue) return;

    const newTitle = document.getElementById("modal-edit-title")?.value.trim();
    const newSeverity = document.getElementById("modal-edit-severity")?.value || "MEDIUM";
    const newCategory = document.getElementById("modal-edit-category")?.value || "General";
    const newSteps = (document.getElementById("modal-edit-steps")?.value || "").trim();
    const newDesc = (document.getElementById("modal-edit-desc")?.value || "").trim();

    if (!newTitle) {
        alert("Title is required.");
        return;
    }

    let fullDescription = "";
    if (newSteps) {
        fullDescription += `### Steps to Reproduce:\n${newSteps}\n\n`;
    }
    if (newDesc) {
        fullDescription += `### Description & Expected vs Actual Result:\n${newDesc}\n\n`;
    }
    fullDescription = fullDescription.trim();

    const saveBtn = document.getElementById("btn-save-edit-issue");
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Saving...`;
    }

    try {
        const payload = {
            title: newTitle,
            severity: newSeverity,
            category: newCategory,
            description: fullDescription
        };

        const res = await apiRequest(`/api/issues/${currentModalIssue.id}`, "PUT", payload);
        if (res.success) {
            alert("Bug details updated successfully!");
            const editPanel = document.getElementById("modal-edit-issue-panel");
            if (editPanel) editPanel.style.display = "none";
            await openIssueDetailModal(currentModalIssue.id);
            await Promise.all([
                loadDashboardIssues(),
                loadIssuesGrid()
            ]);
        } else {
            alert("Failed to update bug: " + res.message);
        }
    } catch (err) {
        console.error("Edit bug error", err);
        alert("An error occurred while saving bug edits.");
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = `<i class="fa-solid fa-check"></i> Save Changes`;
        }
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

// ================= AGILE WORKSPACE: CORE WORKFLOW & BOARDS =================

async function loadAgileWorkspaceView() {
    if (!activeProjectId) {
        if (projects.length > 0) {
            activeProjectId = projects[0].id;
        } else {
            return;
        }
    }
    syncProjectSelectors(activeProjectId);

    // Fetch issues in active project
    const issuesRes = await apiRequest(`/api/projects/${activeProjectId}/issues?size=100`, "GET");
    if (issuesRes.success) {
        m2Issues = issuesRes.data.content || [];
    }

    // Fetch sprints for active project
    const sprintsRes = await apiRequest(`/api/v1/sprints/?projectId=${activeProjectId}`, "GET");
    if (sprintsRes.success) {
        m2Sprints = sprintsRes.data || [];
    }

    // Fetch live activity stream
    await fetchLiveActivityStream();

    // Update Top Metric Counters
    const activeSprintsCount = m2Sprints.filter(s => s.status === "ACTIVE").length;
    const totalVelocity = m2Sprints.reduce((acc, s) => acc + (s.velocity || 0), 0);
    const inWorkflowCount = m2Issues.filter(i => i.status !== "CLOSED").length;
    const totalAuditCount = m2ActivityLogs.length;

    const elSprintsCount = document.getElementById("m2-metric-sprints-count");
    if (elSprintsCount) elSprintsCount.innerText = activeSprintsCount;
    const elVelocityTotal = document.getElementById("m2-metric-velocity-total");
    if (elVelocityTotal) elVelocityTotal.innerText = `${totalVelocity} pts`;
    const elWorkflowCount = document.getElementById("m2-metric-workflow-count");
    if (elWorkflowCount) elWorkflowCount.innerText = inWorkflowCount;
    const elActivityCount = document.getElementById("m2-metric-activity-count");
    if (elActivityCount) elActivityCount.innerText = totalAuditCount;

    // Render components
    renderM2WorkflowBugs();
    renderM2SprintBoard();
}

function renderM2WorkflowBugs() {
    const listEl = document.getElementById("m2-workflow-bugs-list");
    const countEl = document.getElementById("m2-workflow-bugs-count");
    if (!listEl) return;

    const searchInput = document.getElementById("m2-workflow-search");
    const searchVal = (searchInput ? searchInput.value : "").toLowerCase().trim();

    let filtered = m2Issues;
    if (searchVal) {
        filtered = filtered.filter(i =>
            i.title.toLowerCase().includes(searchVal) ||
            i.issue_key.toLowerCase().includes(searchVal) ||
            i.status.toLowerCase().includes(searchVal)
        );
    }

    if (countEl) countEl.innerText = `${filtered.length} Active Bugs`;

    if (filtered.length === 0) {
        listEl.innerHTML = `<div class="empty-state"><i class="fa-solid fa-clipboard-check"></i><p>No active bugs found in this project</p></div>`;
        return;
    }

    const allStatuses = ["REPORTED", "TRIAGED", "OPEN", "IN_PROGRESS", "QA_VERIFICATION", "RESOLVED", "CLOSED"];

    listEl.innerHTML = "";
    filtered.forEach(issue => {
        const card = document.createElement("div");
        card.className = "workflow-bug-card";

        const sev = (issue.severity || "MEDIUM").toLowerCase();
        const pri = (issue.priority || "MEDIUM").toLowerCase();
        const severityBadge = `badge-${sev === 'critical' ? 'crit' : sev === 'high' ? 'high' : sev === 'medium' ? 'med' : 'low'}`;
        const priorityBadge = `badge-${pri === 'critical' ? 'crit' : pri === 'high' ? 'high' : pri === 'medium' ? 'med' : 'low'}`;

        let statusOptionsHtml = allStatuses.map(st =>
            `<option value="${st}" ${issue.status === st ? 'selected' : ''}>${st.replace('_', ' ')}</option>`
        ).join("");

        card.innerHTML = `
            <div class="workflow-bug-main" onclick="openIssueDetailModal(${issue.id})">
                <div class="workflow-bug-header">
                    <strong class="cell-key">${issue.issue_key}</strong>
                    <span class="workflow-bug-title">${escapeHTML(issue.title)}</span>
                </div>
                <div class="workflow-bug-meta">
                    <span class="badge ${severityBadge}">${issue.severity}</span>
                    <span class="badge ${priorityBadge}">${issue.priority}</span>
                    <span><i class="fa-solid fa-user" style="font-size: 0.7rem;"></i> ${issue.assignee ? escapeHTML(issue.assignee.name) : 'Unassigned'}</span>
                </div>
            </div>
            <div class="workflow-bug-actions" onclick="event.stopPropagation()">
                <select class="workflow-status-select" data-issue-id="${issue.id}">
                    ${statusOptionsHtml}
                </select>
                <button class="btn btn-secondary btn-icon" onclick="openIssueDetailModal(${issue.id}, 'tab-triage')" title="Smart Triage & Dev Matcher">
                    <i class="fa-solid fa-wand-magic-sparkles text-primary"></i>
                </button>
            </div>
        `;

        const selectEl = card.querySelector(".workflow-status-select");
        if (selectEl) {
            selectEl.addEventListener("change", (e) => {
                const newStatus = e.target.value;
                handleWorkflowStatusChange(issue.id, newStatus, selectEl);
            });
        }

        listEl.appendChild(card);
    });
}

async function handleWorkflowStatusChange(issueId, newStatus, selectEl) {
    const res = await apiRequest(`/api/issues/${issueId}/status`, "PUT", { status: newStatus });
    if (res.success) {
        await loadAgileWorkspaceView();
        loadDashboardIssues();
    } else {
        alert("Workflow Transition Blocked: " + res.message);
        if (selectEl) {
            const issue = m2Issues.find(i => i.id === issueId);
            if (issue) selectEl.value = issue.status;
        }
    }
}

// ================= LIVE ACTIVITY STREAM =================

async function fetchLiveActivityStream() {
    const res = await apiRequest("/api/v1/collaboration/activity-stream?limit=50", "GET");
    if (res.success) {
        m2ActivityLogs = res.data || [];
        renderM2ActivityStream();
    }
}

function renderM2ActivityStream() {
    const feedEl = document.getElementById("m2-activity-stream-list");
    if (!feedEl) return;

    let filtered = m2ActivityLogs;
    if (m2ActivityFilter !== "ALL") {
        filtered = filtered.filter(l => l.action === m2ActivityFilter);
    }

    if (filtered.length === 0) {
        feedEl.innerHTML = `<div class="empty-state"><i class="fa-solid fa-clock-rotate-left"></i><p>No activity records for this filter</p></div>`;
        return;
    }

    feedEl.innerHTML = "";
    filtered.forEach(log => {
        const item = document.createElement("div");
        item.className = "activity-item";

        const userName = log.performed_by ? log.performed_by.name : "System";
        const initials = userName.split(" ").map(n => n[0]).join("").substring(0, 2).toUpperCase();

        let diffHtml = "";
        if (log.old_value || log.new_value) {
            diffHtml = `<div class="activity-diff-pill"><span>${escapeHTML(log.old_value || 'None')}</span> <i class="fa-solid fa-arrow-right" style="font-size: 0.65rem;"></i> <strong style="color: var(--color-primary);">${escapeHTML(log.new_value || 'None')}</strong></div>`;
        }

        let issueRef = "";
        if (log.issue) {
            issueRef = `<span class="activity-issue-link" onclick="openIssueDetailModal(${log.issue.id})">${log.issue.issue_key}: ${escapeHTML(log.issue.title)}</span>`;
        } else if (log.issue_id) {
            issueRef = `<span class="activity-issue-link" onclick="openIssueDetailModal(${log.issue_id})">Issue #${log.issue_id}</span>`;
        }

        const dateObj = new Date(log.timestamp);
        const timeStr = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        const actionBadgeClass = log.action === 'STATUS_CHANGED' ? 'badge-primary' :
                                 log.action === 'SPRINT_ASSIGNED' ? 'badge-med' :
                                 log.action === 'COMMENT_ADDED' ? 'badge-high' : 'badge-info';

        item.innerHTML = `
            <div class="activity-avatar">${initials}</div>
            <div class="activity-content">
                <div class="activity-user-row">
                    <span class="activity-username">${escapeHTML(userName)}</span>
                    <span class="activity-time">${timeStr}</span>
                </div>
                <div class="activity-desc">
                    <span class="badge ${actionBadgeClass}">${log.action.replace('_', ' ')}</span>
                    ${issueRef ? ' on ' + issueRef : ''}
                </div>
                ${diffHtml}
            </div>
        `;
        feedEl.appendChild(item);
    });
}

// ================= AGILE SPRINTS & BACKLOG =================

function renderM2SprintBoard() {
    const sprintsEl = document.getElementById("m2-sprints-container");
    const backlogEl = document.getElementById("m2-backlog-container");
    const sprintsBadge = document.getElementById("m2-sprints-total-badge");
    const backlogBadge = document.getElementById("m2-backlog-count-badge");

    if (!sprintsEl || !backlogEl) return;

    // Left Column: Sprints
    if (sprintsBadge) sprintsBadge.innerText = `${m2Sprints.length} Sprints`;
    if (m2Sprints.length === 0) {
        sprintsEl.innerHTML = `<div class="empty-state"><i class="fa-solid fa-arrows-spin"></i><p>No sprints created yet. Click "Create Sprint" above.</p></div>`;
    } else {
        sprintsEl.innerHTML = "";
        m2Sprints.forEach(sprint => {
            const card = document.createElement("div");
            card.className = "sprint-card";

            const issuesInSprint = sprint.issues || m2Issues.filter(i => i.sprint_id === sprint.id);
            const resolvedCount = sprint.resolved_issues !== undefined ? sprint.resolved_issues : issuesInSprint.filter(i => i.status === "RESOLVED" || i.status === "CLOSED").length;
            const totalCount = sprint.total_issues !== undefined ? sprint.total_issues : issuesInSprint.length;
            const progressPct = sprint.progress_percentage !== undefined ? sprint.progress_percentage : (totalCount > 0 ? Math.round((resolvedCount / totalCount) * 100) : 0);

            const statusClass = sprint.status === "ACTIVE" ? "badge-crit" : sprint.status === "COMPLETED" ? "badge-low" : "badge-med";

            let completeBtn = "";
            if (sprint.status === "ACTIVE") {
                completeBtn = `
                    <button class="btn btn-secondary" onclick="handleCompleteSprint(${sprint.id})" title="Complete Sprint and Calculate Velocity">
                        <i class="fa-solid fa-flag-checkered"></i> Complete Sprint
                    </button>
                `;
            }

            let issuesListHtml = "";
            if (issuesInSprint.length === 0) {
                issuesListHtml = `<span class="text-muted" style="font-size: 0.8rem;">No issues assigned to this sprint. Assign from Backlog on the right.</span>`;
            } else {
                issuesListHtml = issuesInSprint.map(i => {
                    const iPri = (i.priority || "MEDIUM").toLowerCase();
                    const iBadge = iPri === 'critical' ? 'badge-crit' : iPri === 'high' ? 'badge-high' : 'badge-med';
                    return `
                        <div class="sprint-issue-mini-row" onclick="openIssueDetailModal(${i.id})">
                            <div>
                                <strong class="cell-key">${i.issue_key}</strong>
                                <span>${escapeHTML(i.title)}</span>
                            </div>
                            <div style="display: flex; align-items: center; gap: 6px;">
                                <span class="capsule capsule-${i.status.toLowerCase().replace('_', '-')}">${i.status}</span>
                                <span class="badge ${iBadge}">${i.priority}</span>
                            </div>
                        </div>
                    `;
                }).join("");
            }

            card.innerHTML = `
                <div class="sprint-card-header">
                    <div class="sprint-title-area">
                        <h4>${escapeHTML(sprint.name)}</h4>
                        <p class="sprint-goal-text">${escapeHTML(sprint.goal || 'No goal set')}</p>
                    </div>
                    <div class="sprint-badges">
                        <span class="badge ${statusClass}">${sprint.status}</span>
                        <span class="priority-score-badge">Velocity: ${sprint.velocity || 0} pts</span>
                    </div>
                </div>
                <div class="sprint-dates">
                    <i class="fa-solid fa-calendar-days"></i>
                    <span>${sprint.start_date ? new Date(sprint.start_date).toLocaleDateString() : 'TBD'} - ${sprint.end_date ? new Date(sprint.end_date).toLocaleDateString() : 'TBD'}</span>
                </div>
                <div class="sprint-progress-wrapper">
                    <div class="sprint-progress-labels">
                        <span>Sprint Progress (${resolvedCount}/${totalCount} resolved)</span>
                        <strong>${progressPct}%</strong>
                    </div>
                    <div class="sprint-progress-track">
                        <div class="sprint-progress-fill" style="width: ${progressPct}%;"></div>
                    </div>
                </div>
                <div class="sprint-issues-list">
                    ${issuesListHtml}
                </div>
                <div class="sprint-actions-footer">
                    ${completeBtn}
                </div>
            `;
            sprintsEl.appendChild(card);
        });
    }

    // Right Column: Product Backlog (issues with sprint_id === null)
    const backlogIssues = m2Issues.filter(i => !i.sprint_id);
    if (backlogBadge) backlogBadge.innerText = `${backlogIssues.length} Issues`;

    if (backlogIssues.length === 0) {
        backlogEl.innerHTML = `<div class="empty-state"><i class="fa-solid fa-circle-check"></i><p>Backlog is empty. All issues assigned to sprints!</p></div>`;
    } else {
        backlogEl.innerHTML = "";
        const activeSprints = m2Sprints.filter(s => s.status !== "COMPLETED");

        backlogIssues.forEach(issue => {
            const card = document.createElement("div");
            card.className = "backlog-issue-card";

            const bSev = (issue.severity || "MEDIUM").toLowerCase();
            const severityBadge = `badge-${bSev === 'critical' ? 'crit' : bSev === 'high' ? 'high' : 'badge-low'}`;

            let sprintOptionsHtml = activeSprints.map(s =>
                `<option value="${s.id}">${escapeHTML(s.name)}</option>`
            ).join("");

            let assignActionHtml = "";
            if (activeSprints.length === 0) {
                assignActionHtml = `<span class="text-muted" style="font-size: 0.75rem;">Create a sprint to assign</span>`;
            } else {
                assignActionHtml = `
                    <div class="backlog-assign-sprint-form" onclick="event.stopPropagation()">
                        <select class="filter-select" id="backlog-sprint-select-${issue.id}" style="padding: 4px 8px; font-size: 0.78rem;">
                            ${sprintOptionsHtml}
                        </select>
                        <button class="btn btn-primary btn-icon" style="padding: 4px 8px; font-size: 0.75rem;" onclick="handleAddIssueToSprint(${issue.id}, 'backlog-sprint-select-${issue.id}')" title="Assign to Sprint">
                            <i class="fa-solid fa-plus"></i> Add
                        </button>
                    </div>
                `;
            }

            card.innerHTML = `
                <div class="backlog-card-top" onclick="openIssueDetailModal(${issue.id})">
                    <strong class="cell-key">${issue.issue_key}</strong>
                    <span class="badge ${severityBadge}">${issue.severity}</span>
                </div>
                <div class="backlog-card-title" onclick="openIssueDetailModal(${issue.id})">
                    ${escapeHTML(issue.title)}
                </div>
                <div class="backlog-card-footer">
                    <span class="text-muted" style="font-size: 0.78rem;">Reporter: ${issue.reporter ? escapeHTML(issue.reporter.name) : 'Unknown'}</span>
                    ${assignActionHtml}
                </div>
            `;
            backlogEl.appendChild(card);
        });
    }
}

async function handleAddIssueToSprint(issueId, selectElementId) {
    const selectEl = document.getElementById(selectElementId);
    if (!selectEl) return;
    const sprintId = parseInt(selectEl.value);
    if (!sprintId) return;

    const res = await apiRequest(`/api/v1/sprints/${sprintId}/add-issue/${issueId}`, "POST");
    if (res.success) {
        await loadAgileWorkspaceView();
    } else {
        alert("Failed to add issue to sprint: " + res.message);
    }
}

async function handleCompleteSprint(sprintId) {
    if (!confirm("Complete this sprint and calculate total velocity achieved?")) return;

    const res = await apiRequest(`/api/v1/sprints/${sprintId}/status`, "PUT", { status: "COMPLETED" });
    if (res.success) {
        alert(`Sprint completed! Final Velocity Achieved: ${res.data.velocity || 0} points.`);
        await loadAgileWorkspaceView();
    } else {
        alert("Failed to complete sprint: " + res.message);
    }
}

async function handleCreateSprint(e) {
    e.preventDefault();
    const projectId = parseInt(document.getElementById("sprint-project-select").value);
    const name = document.getElementById("sprint-name-input").value;
    const goal = document.getElementById("sprint-goal-input").value;
    const startDate = document.getElementById("sprint-start-date").value;
    const endDate = document.getElementById("sprint-end-date").value;

    const res = await apiRequest("/api/v1/sprints/", "POST", {
        project_id: projectId,
        name,
        goal,
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString()
    });

    if (res.success) {
        alert("Sprint created successfully!");
        document.getElementById("create-sprint-form").reset();
        document.getElementById("create-sprint-modal").style.display = "none";
        await loadAgileWorkspaceView();
    } else {
        alert("Sprint creation failed: " + res.message);
    }
}

// ================= SMART TRIAGE & DEV MATCHING =================

async function handleRunSmartTriage() {
    if (!currentModalIssue) return;
    const category = document.getElementById("modal-triage-category").value;

    const triageRes = await apiRequest("/api/v1/issues/triage-recommendation", "POST", {
        title: currentModalIssue.title,
        description: currentModalIssue.description || "",
        severity: currentModalIssue.severity,
        category: category
    });

    if (triageRes.success) {
        const pData = triageRes.data;
        const devs = pData.recommended_developers || [];

        // Render Priority Score Card
        document.getElementById("triage-score-display").innerText = pData.priority_score.toFixed(1);
        const tierBadge = document.getElementById("triage-priority-tier-badge");
        tierBadge.innerText = pData.recommended_priority;
        tierBadge.className = `badge ${pData.recommended_priority === 'URGENT' ? 'badge-crit' : pData.recommended_priority === 'HIGH' ? 'badge-high' : 'badge-med'}`;

        document.getElementById("triage-formula-text").innerText = pData.formula ||
            `Severity: ${pData.severity} (${pData.severity_weight}) × Category Urgency: ${pData.category_urgency_weight} = Priority Score: ${pData.priority_score.toFixed(1)}`;

        // Render Dev Matches
        const devsList = document.getElementById("modal-dev-matches-list");
        devsList.innerHTML = "";

        if (devs.length === 0) {
            devsList.innerHTML = `<p class="text-muted">No developer profiles match the criteria.</p>`;
        } else {
            devs.forEach(dev => {
                const card = document.createElement("div");
                card.className = "dev-match-card";

                const matchPct = dev.match_percentage || 0;
                const skillsArray = dev.skills ? dev.skills.split(',').map(s => s.trim()).filter(s => s) : [];
                const skillsHtml = skillsArray.map(s => `<span class="badge badge-info" style="font-size: 0.68rem;">${escapeHTML(s)}</span>`).join(" ");

                card.innerHTML = `
                    <div class="dev-match-info">
                        <div class="dev-match-name">
                            <span>${escapeHTML(dev.name)}</span>
                            <span class="badge badge-low" style="font-size: 0.7rem;">${matchPct}% Match</span>
                            <span class="badge badge-med" style="font-size: 0.7rem;">${dev.active_tasks} active tasks</span>
                        </div>
                        <div class="dev-match-score-bar-wrap">
                            <div class="dev-match-score-bar-fill" style="width: ${matchPct}%;"></div>
                        </div>
                        <div style="margin-top: 4px; display: flex; gap: 4px; flex-wrap: wrap;">
                            ${skillsHtml}
                        </div>
                        <p class="dev-match-reason">${escapeHTML(dev.rationale || '')}</p>
                    </div>
                    <button class="btn btn-primary" onclick="handleAssignFromTriage(${currentModalIssue.id}, ${dev.developer_id})">
                        <i class="fa-solid fa-user-plus"></i> Assign
                    </button>
                `;
                devsList.appendChild(card);
            });
        }

        document.getElementById("modal-triage-results").style.display = "flex";
    } else {
        alert("Smart Triage calculation failed: " + (triageRes.message || "Unknown error"));
    }
}

async function handleAssignFromTriage(issueId, devId) {
    const res = await apiRequest(`/api/issues/${issueId}/assign`, "PUT", { assignee_id: devId });
    if (res.success) {
        alert("Developer assigned successfully!");
        await openIssueDetailModal(issueId, "tab-triage");
        loadAgileWorkspaceView();
        loadDashboardIssues();
    } else {
        alert("Failed to assign: " + res.message);
    }
}

// ================= COMMENTS & DISCUSSION =================

async function loadModalComments(issueId) {
    const listEl = document.getElementById("modal-comments-list");
    const countEl = document.getElementById("modal-comments-count");
    if (!listEl) return;
    listEl.innerHTML = "";

    const res = await apiRequest(`/api/v1/collaboration/issues/${issueId}/comments`, "GET");
    if (res.success) {
        const comments = res.data || [];
        if (countEl) countEl.innerText = comments.length;

        if (comments.length === 0) {
            listEl.innerHTML = `<span class="text-muted" style="font-size: 0.85rem;">No discussion comments yet. Start the conversation below.</span>`;
            return;
        }

        comments.forEach(c => {
            const bubble = document.createElement("div");
            bubble.className = "comment-bubble";

            const authorName = c.user ? c.user.name : "User";
            const authorRole = c.user ? c.user.role : "USER";
            const initials = authorName.split(" ").map(n => n[0]).join("").substring(0, 2).toUpperCase();
            const timeStr = new Date(c.created_at).toLocaleString();

            bubble.innerHTML = `
                <div class="comment-avatar">${initials}</div>
                <div class="comment-body-wrapper">
                    <div class="comment-meta-row">
                        <span class="comment-author-name">
                            ${escapeHTML(authorName)}
                            <span class="badge ${authorRole === 'ADMIN' ? 'badge-crit' : authorRole === 'DEVELOPER' ? 'badge-primary' : 'badge-med'}" style="font-size: 0.65rem;">${authorRole}</span>
                        </span>
                        <span class="activity-time">${timeStr}</span>
                    </div>
                    <div class="comment-text">${escapeHTML(c.content)}</div>
                </div>
            `;
            listEl.appendChild(bubble);
        });
        listEl.scrollTop = listEl.scrollHeight;
    }
}

async function handleAddComment(e) {
    e.preventDefault();
    if (!currentModalIssue) return;

    const textarea = document.getElementById("modal-new-comment-text");
    const content = textarea.value.trim();
    if (!content) return;

    const res = await apiRequest(`/api/v1/collaboration/issues/${currentModalIssue.id}/comments`, "POST", { content });
    if (res.success) {
        textarea.value = "";
        await loadModalComments(currentModalIssue.id);
        fetchLiveActivityStream();
    } else {
        alert("Failed to post comment: " + res.message);
    }
}

// ================= FILE ATTACHMENTS =================

async function loadModalAttachments(issueId) {
    const gridEl = document.getElementById("modal-attachments-list");
    const countEl = document.getElementById("modal-attachments-count");
    if (!gridEl) return;
    gridEl.innerHTML = "";

    const res = await apiRequest(`/api/v1/collaboration/issues/${issueId}/attachments`, "GET");
    if (res.success) {
        const attachments = res.data || [];
        if (countEl) countEl.innerText = attachments.length;

        if (attachments.length === 0) {
            gridEl.innerHTML = `<span class="text-muted" style="font-size: 0.85rem;">No files attached to this issue.</span>`;
            return;
        }

        attachments.forEach(att => {
            const card = document.createElement("div");
            card.className = "attachment-card";

            const isImg = att.content_type && att.content_type.startsWith("image/");
            const iconClass = isImg ? "fa-file-image" : "fa-file-code";
            const sizeKb = Math.round(att.file_size / 1024);

            card.innerHTML = `
                <i class="fa-solid ${iconClass} attachment-icon"></i>
                <div class="attachment-details">
                    <div class="attachment-name" title="${escapeHTML(att.filename)}">${escapeHTML(att.filename)}</div>
                    <div class="attachment-meta">${sizeKb} KB • ${new Date(att.uploaded_at).toLocaleDateString()}</div>
                </div>
                <a href="/api/v1/collaboration/attachments/${att.id}/download" target="_blank" class="btn btn-secondary btn-icon" title="Download">
                    <i class="fa-solid fa-download"></i>
                </a>
            `;
            gridEl.appendChild(card);
        });
    }
}

async function handleUploadAttachment() {
    if (!currentModalIssue) return;
    const fileInput = document.getElementById("modal-attachment-file-input");
    if (!fileInput.files || fileInput.files.length === 0) return;

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append("file", file);

    const headers = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    try {
        const response = await fetch(`/api/v1/collaboration/issues/${currentModalIssue.id}/attachments`, {
            method: "POST",
            headers,
            body: formData
        });
        const res = await response.json();
        if (res.success) {
            fileInput.value = "";
            document.getElementById("modal-selected-filename").innerText = "No file chosen";
            document.getElementById("btn-submit-attachment").disabled = true;
            await loadModalAttachments(currentModalIssue.id);
            fetchLiveActivityStream();
            alert("File attached successfully!");
        } else {
            alert("Upload failed: " + res.message);
        }
    } catch (err) {
        console.error("Upload error", err);
        alert("Upload failed due to connection error.");
    }
}

// ================= AGILE QUALITY & SPRINT PDF REPORT =================

function handleGeneratePdfReport() {
    const reportContent = document.getElementById("printable-report-content");
    const project = projects.find(p => p.id === activeProjectId);
    const projectName = project ? project.name : "Active Project";
    const projectKey = project ? project.project_key : "PROJ";

    const totalIssues = m2Issues.length;
    const activeIssues = m2Issues.filter(i => i.status !== "CLOSED").length;
    const resolvedIssues = m2Issues.filter(i => i.status === "RESOLVED" || i.status === "CLOSED").length;
    const criticalIssues = m2Issues.filter(i => i.severity === "CRITICAL").length;
    const totalVelocity = m2Sprints.reduce((acc, s) => acc + (s.velocity || 0), 0);

    const sprintsRows = m2Sprints.map(s => `
        <tr>
            <td><strong>${escapeHTML(s.name)}</strong></td>
            <td><span class="badge ${s.status === 'ACTIVE' ? 'badge-crit' : 'badge-low'}">${s.status}</span></td>
            <td>${s.velocity || 0} pts</td>
            <td>${s.total_issues !== undefined ? s.total_issues : (s.issues || []).length} issues</td>
            <td>${s.start_date ? new Date(s.start_date).toLocaleDateString() : '-'} - ${s.end_date ? new Date(s.end_date).toLocaleDateString() : '-'}</td>
        </tr>
    `).join("");

    const topIssuesRows = m2Issues.slice(0, 10).map(i => `
        <tr>
            <td><strong>${i.issue_key}</strong></td>
            <td>${escapeHTML(i.title)}</td>
            <td><span class="badge ${i.severity === 'CRITICAL' ? 'badge-crit' : 'badge-high'}">${i.severity}</span></td>
            <td><span class="capsule capsule-${i.status.toLowerCase().replace('_', '-')}">${i.status}</span></td>
            <td>${i.assignee ? escapeHTML(i.assignee.name) : 'Unassigned'}</td>
        </tr>
    `).join("");

    reportContent.innerHTML = `
        <div style="padding: 10px 0; border-bottom: 2px solid #6366f1; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1 style="font-size: 1.6rem; color: #6366f1; margin-bottom: 4px;">BugFlow Quality & Sprint Audit Report</h1>
                    <p style="color: #64748b; font-size: 0.9rem;">Project: <strong>${escapeHTML(projectName)} [${projectKey}]</strong></p>
                </div>
                <div style="text-align: right; color: #64748b; font-size: 0.8rem;">
                    Generated: ${new Date().toLocaleString()}<br>
                    Agile Workspace Executive Summary
                </div>
            </div>
        </div>

        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 24px;">
            <div style="border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Total Issues</div>
                <div style="font-size: 1.8rem; font-weight: 700;">${totalIssues}</div>
            </div>
            <div style="border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">In Active Workflow</div>
                <div style="font-size: 1.8rem; font-weight: 700; color: #f59e0b;">${activeIssues}</div>
            </div>
            <div style="border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Resolved / Closed</div>
                <div style="font-size: 1.8rem; font-weight: 700; color: #10b981;">${resolvedIssues}</div>
            </div>
            <div style="border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Velocity Achieved</div>
                <div style="font-size: 1.8rem; font-weight: 700; color: #6366f1;">${totalVelocity} pts</div>
            </div>
        </div>

        <h3 style="margin-bottom: 10px; font-size: 1.1rem;"><i class="fa-solid fa-arrows-spin text-primary"></i> Sprint Performance Overview</h3>
        <table class="issues-table" style="margin-bottom: 24px;">
            <thead>
                <tr>
                    <th>Sprint Name</th>
                    <th>Status</th>
                    <th>Velocity</th>
                    <th>Issues Count</th>
                    <th>Date Range</th>
                </tr>
            </thead>
            <tbody>
                ${sprintsRows || '<tr><td colspan="5">No sprints recorded</td></tr>'}
            </tbody>
        </table>

        <h3 style="margin-bottom: 10px; font-size: 1.1rem;"><i class="fa-solid fa-bug text-primary"></i> Priority Issues & Defect Status</h3>
        <table class="issues-table">
            <thead>
                <tr>
                    <th>Key</th>
                    <th>Title</th>
                    <th>Severity</th>
                    <th>Status</th>
                    <th>Assignee</th>
                </tr>
            </thead>
            <tbody>
                ${topIssuesRows || '<tr><td colspan="5">No issues recorded</td></tr>'}
            </tbody>
        </table>
    `;

    document.getElementById("pdf-report-modal").style.display = "flex";
}

// ==========================================================================
// MILESTONE 3: ANALYTICS, PLOTLY VISUALIZATIONS, WEBHOOK BOT & API EXPLORER
// ==========================================================================

async function loadMilestone3Dashboard() {
    try {
        console.log("Loading Milestone 3 Quality Analytics & Charts...");

        // 1. Fetch Quality Metrics Scorecard
        const metricsRes = await fetch("/api/v1/analytics/quality-metrics");
        if (metricsRes.ok) {
            const metricsJson = await metricsRes.json();
            if (metricsJson.success && metricsJson.data) {
                const m = metricsJson.data;

                // Fix Rate %
                const elFixRate = document.getElementById("m3-fix-rate");
                const elFixBar = document.getElementById("m3-fix-rate-bar");
                const elFixSub = document.getElementById("m3-fix-rate-sub");
                if (elFixRate) elFixRate.innerText = `${m.fix_rate_percentage}%`;
                if (elFixBar) elFixBar.style.width = `${Math.min(100, m.fix_rate_percentage)}%`;
                if (elFixSub) elFixSub.innerText = `${m.resolved_bugs + m.closed_bugs} Fixed / ${m.total_bugs} Total Bugs`;

                // MTTR
                const elMttr = document.getElementById("m3-mttr");
                const elMttrSub = document.getElementById("m3-mttr-sub");
                if (elMttr) elMttr.innerText = m.mttr_formatted || `${m.mean_time_to_resolution_hours} hrs`;
                if (elMttrSub) {
                    const slaText = m.mttr_sla_compliance_rate !== undefined ? ` • SLA Met: ${m.mttr_sla_compliance_rate}%` : '';
                    elMttrSub.innerText = `Average resolution: ${m.mean_time_to_resolution_hours} hrs${slaText}`;
                }

                // Defect Leakage Rate %
                const elLeak = document.getElementById("m3-leakage");
                const elLeakSub = document.getElementById("m3-leakage-sub");
                if (elLeak) elLeak.innerText = `${m.defect_leakage_rate_percentage}%`;
                if (elLeakSub) elLeakSub.innerText = `${m.production_bugs} Found in Prod / ${m.total_bugs} Total`;

                // Backlog Health Score
                const elHealth = document.getElementById("m3-health-score");
                const elHealthBadge = document.getElementById("m3-health-badge");
                const elHealthVerdict = document.getElementById("m3-health-verdict");
                if (elHealth) elHealth.innerText = `${m.backlog_health_score} / 100`;
                if (elHealthVerdict) elHealthVerdict.innerText = m.health_verdict || "Release readiness evaluated";
                if (elHealthBadge) {
                    elHealthBadge.innerText = m.health_status || "HEALTHY";
                    elHealthBadge.className = `badge ${m.backlog_health_score >= 85 ? 'badge-low' : (m.backlog_health_score >= 60 ? 'badge-med' : 'badge-crit')}`;
                }
            }
        }

        // 2. Fetch Plotly Charts Configuration
        const chartsRes = await fetch("/api/v1/analytics/plotly-charts");
        if (chartsRes.ok) {
            const chartsJson = await chartsRes.json();
            if (chartsJson.success && chartsJson.data) {
                renderMilestone3PlotlyCharts(chartsJson.data);
            }
        }
    } catch (err) {
        console.error("Failed to load Milestone 3 dashboard data:", err);
    }
}

function renderMilestone3PlotlyCharts(chartsData) {
    if (typeof Plotly === "undefined") {
        console.warn("Plotly.js library not loaded yet.");
        return;
    }

    // Common dark theme layout overrides for seamless aesthetic integration
    const darkLayoutBase = {
        paper_bgcolor: 'rgba(0, 0, 0, 0)',
        plot_bgcolor: 'rgba(0, 0, 0, 0)',
        font: {
            family: 'Inter, Outfit, sans-serif',
            color: '#94a3b8'
        }
    };

    // 1. Defect Trend (Last 14 Days)
    if (chartsData.trend_chart && document.getElementById("m3-plotly-trend")) {
        const trendLayout = {
            ...chartsData.trend_chart.layout,
            ...darkLayoutBase,
            xaxis: {
                ...chartsData.trend_chart.layout.xaxis,
                gridcolor: 'rgba(255, 255, 255, 0.06)',
                zerolinecolor: 'rgba(255, 255, 255, 0.1)',
                tickfont: { color: '#94a3b8' }
            },
            yaxis: {
                ...chartsData.trend_chart.layout.yaxis,
                gridcolor: 'rgba(255, 255, 255, 0.06)',
                zerolinecolor: 'rgba(255, 255, 255, 0.1)',
                tickfont: { color: '#94a3b8' }
            },
            legend: {
                font: { color: '#f8fafc' },
                orientation: 'h',
                y: 1.15,
                x: 0.5,
                xanchor: 'center'
            }
        };
        Plotly.newPlot("m3-plotly-trend", chartsData.trend_chart.data, trendLayout, {
            responsive: true,
            displayModeBar: false
        });
    }

    // 2. Severity Donut Chart
    if (chartsData.severity_chart && document.getElementById("m3-plotly-severity")) {
        const severityLayout = {
            ...chartsData.severity_chart.layout,
            ...darkLayoutBase,
            legend: {
                font: { color: '#f8fafc' },
                orientation: 'h',
                y: -0.15,
                x: 0.5,
                xanchor: 'center'
            }
        };
        Plotly.newPlot("m3-plotly-severity", chartsData.severity_chart.data, severityLayout, {
            responsive: true,
            displayModeBar: false
        });
    }

    // 3. Workflow Pipeline Bar Chart
    if (chartsData.workflow_chart && document.getElementById("m3-plotly-workflow")) {
        const workflowLayout = {
            ...chartsData.workflow_chart.layout,
            ...darkLayoutBase,
            xaxis: {
                ...chartsData.workflow_chart.layout.xaxis,
                gridcolor: 'rgba(255, 255, 255, 0.06)',
                tickfont: { color: '#94a3b8' }
            },
            yaxis: {
                ...chartsData.workflow_chart.layout.yaxis,
                gridcolor: 'rgba(255, 255, 255, 0.06)',
                tickfont: { color: '#94a3b8' }
            }
        };
        Plotly.newPlot("m3-plotly-workflow", chartsData.workflow_chart.data, workflowLayout, {
            responsive: true,
            displayModeBar: false
        });
    }

    // 4. Mean Time to Resolution (MTTR) by Priority vs SLA Target
    if (chartsData.mttr_chart && document.getElementById("m3-plotly-mttr")) {
        const mttrLayout = {
            ...chartsData.mttr_chart.layout,
            ...darkLayoutBase,
            title: '', // Hide internal title (card header displays title instead)
            xaxis: {
                ...chartsData.mttr_chart.layout.xaxis,
                gridcolor: 'rgba(255, 255, 255, 0.06)',
                tickfont: { color: '#94a3b8' },
                title: {
                    ...(typeof chartsData.mttr_chart.layout.xaxis?.title === 'object' ? chartsData.mttr_chart.layout.xaxis.title : { text: chartsData.mttr_chart.layout.xaxis?.title || 'Priority Tier' }),
                    font: { color: '#cbd5e1' }
                }
            },
            yaxis: {
                ...chartsData.mttr_chart.layout.yaxis,
                gridcolor: 'rgba(255, 255, 255, 0.06)',
                tickfont: { color: '#94a3b8' },
                title: {
                    ...(typeof chartsData.mttr_chart.layout.yaxis?.title === 'object' ? chartsData.mttr_chart.layout.yaxis.title : { text: chartsData.mttr_chart.layout.yaxis?.title || 'Resolution Time (Hours)' }),
                    font: { color: '#cbd5e1' }
                }
            },
            legend: {
                font: { color: '#f8fafc' },
                orientation: 'h',
                y: 1.15,
                x: 0.5,
                xanchor: 'center'
            }
        };
        Plotly.newPlot("m3-plotly-mttr", chartsData.mttr_chart.data, mttrLayout, {
            responsive: true,
            displayModeBar: false
        });
    }

    // 5. Individual Defect Time to Resolution (TTR) Timeline
    if (chartsData.ttr_chart && document.getElementById("m3-plotly-ttr")) {
        const ttrLayout = {
            ...chartsData.ttr_chart.layout,
            ...darkLayoutBase,
            title: '', // Hide internal title (card header displays title instead)
            xaxis: {
                ...chartsData.ttr_chart.layout.xaxis,
                gridcolor: 'rgba(255, 255, 255, 0.06)',
                tickfont: { color: '#94a3b8' },
                title: {
                    ...(typeof chartsData.ttr_chart.layout.xaxis?.title === 'object' ? chartsData.ttr_chart.layout.xaxis.title : { text: chartsData.ttr_chart.layout.xaxis?.title || 'Resolved Defect' }),
                    font: { color: '#cbd5e1' }
                }
            },
            yaxis: {
                ...chartsData.ttr_chart.layout.yaxis,
                gridcolor: 'rgba(255, 255, 255, 0.06)',
                tickfont: { color: '#94a3b8' },
                title: {
                    ...(typeof chartsData.ttr_chart.layout.yaxis?.title === 'object' ? chartsData.ttr_chart.layout.yaxis.title : { text: chartsData.ttr_chart.layout.yaxis?.title || 'Time to Resolution (Hours)' }),
                    font: { color: '#cbd5e1' }
                }
            },
            legend: {
                font: { color: '#f8fafc' },
                orientation: 'h',
                y: 1.15,
                x: 0.5,
                xanchor: 'center'
            }
        };
        Plotly.newPlot("m3-plotly-ttr", chartsData.ttr_chart.data, ttrLayout, {
            responsive: true,
            displayModeBar: false
        });
    }
}

// Switch between MTTR by Priority view and Individual Defect TTR Timeline view
function switchMttrView(view) {
    const elMttr = document.getElementById("m3-plotly-mttr");
    const elTtr = document.getElementById("m3-plotly-ttr");
    const btnPri = document.getElementById("btn-mttr-view-priority");
    const btnTtr = document.getElementById("btn-mttr-view-ttr");
    const cardTitle = document.getElementById("m3-mttr-card-title");
    const cardSubtitle = document.getElementById("m3-mttr-card-subtitle");

    if (view === "priority") {
        if (elMttr) elMttr.style.display = "block";
        if (elTtr) elTtr.style.display = "none";
        if (btnPri) { btnPri.classList.add("btn-primary", "active"); btnPri.classList.remove("btn-secondary"); }
        if (btnTtr) { btnTtr.classList.remove("btn-primary", "active"); btnTtr.classList.add("btn-secondary"); }
        if (cardTitle) cardTitle.innerHTML = '<i class="fa-solid fa-stopwatch text-progress"></i> Mean Time to Resolution (MTTR) & SLA Performance';
        if (cardSubtitle) cardSubtitle.innerText = 'Average resolution hours vs engineering SLA benchmarks across priority tiers';
        if (typeof Plotly !== "undefined" && elMttr) Plotly.Plots.resize(elMttr);
    } else {
        if (elMttr) elMttr.style.display = "none";
        if (elTtr) elTtr.style.display = "block";
        if (btnTtr) { btnTtr.classList.add("btn-primary", "active"); btnTtr.classList.remove("btn-secondary"); }
        if (btnPri) { btnPri.classList.remove("btn-primary", "active"); btnPri.classList.add("btn-secondary"); }
        if (cardTitle) cardTitle.innerHTML = '<i class="fa-solid fa-timeline text-progress"></i> Individual Defect Resolution Time (TTR) Analysis';
        if (cardSubtitle) cardSubtitle.innerText = 'Time to resolution (hours) per resolved defect compared against target SLA limits';
        if (typeof Plotly !== "undefined" && elTtr) Plotly.Plots.resize(elTtr);
    }
}

// Webhook Simulator
async function simulateGitWebhook() {
    const commitMsg = document.getElementById("m3-commit-message")?.value || "fixes #2 login password crash";
    const commitSha = document.getElementById("m3-commit-sha")?.value || "a7f8c92";

    const consoleBox = document.getElementById("m3-webhook-console");
    const consoleOutput = document.getElementById("m3-webhook-output");
    const statusBadge = document.getElementById("m3-webhook-status-badge");

    if (consoleBox) consoleBox.style.display = "block";
    if (consoleOutput) consoleOutput.innerText = `[CI/CD Sync] Sending webhook request to POST /api/v1/webhooks/git...\nPayload: ${JSON.stringify({ commit_message: commitMsg, commit_hash: commitSha }, null, 2)}`;

    try {
        const response = await fetch("/api/v1/webhooks/git", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                commit_message: commitMsg,
                commit_hash: commitSha,
                author: currentUser?.name || "Developer",
                branch: "main"
            })
        });

        const resData = await response.json();

        if (statusBadge) {
            statusBadge.innerText = `${response.status} ${response.statusText || 'OK'}`;
            statusBadge.className = `badge ${response.ok ? 'badge-low' : 'badge-crit'}`;
        }

        if (consoleOutput) {
            consoleOutput.innerText = JSON.stringify(resData, null, 2);
        }

        if (response.ok && resData.success) {
            const updated = resData.data.updated_issues || [];
            let detailStr = updated.map(u => `${u.issue_key} (Now: ${u.new_status})`).join(", ");
            alert(`CI/CD Webhook Success!\n${resData.message}\n${detailStr ? "Auto-transitioned: " + detailStr : "No matching issue keys in message"}`);
            
            // Live refresh Milestone 3 metrics and charts
            loadMilestone3Dashboard();

            // Also reload Agile Workspace and Issues Grid so state change is reflected everywhere
            if (typeof loadAgileWorkspaceView === "function") loadAgileWorkspaceView();
            if (typeof loadIssuesGrid === "function") loadIssuesGrid();
            if (typeof loadDashboardIssues === "function") loadDashboardIssues();
        } else {
            alert(`Webhook execution note: ${resData.message || 'Check payload format'}`);
        }
    } catch (err) {
        console.error("Webhook simulation failed:", err);
        if (consoleOutput) consoleOutput.innerText = `Error: ${err.message}`;
    }
}

// REST API Explorer
function handleApiPresetChange(e) {
    const val = e.target.value;
    const parts = val.split("|");
    const method = parts[0];
    const url = parts[1];

    const methodLabel = document.getElementById("m3-api-method-label");
    const urlInput = document.getElementById("m3-api-url-input");
    const bodyWrapper = document.getElementById("m3-api-body-wrapper");
    const bodyInput = document.getElementById("m3-api-body-input");

    if (methodLabel) {
        methodLabel.innerText = method;
        methodLabel.style.backgroundColor = method === "POST" ? "#f59e0b" : "#2563eb";
    }
    if (urlInput) urlInput.value = url;

    if (bodyWrapper) {
        if (method === "POST") {
            bodyWrapper.style.display = "block";
            if (url.includes("webhooks/git")) {
                bodyInput.value = JSON.stringify({
                    commit_message: "Merge PR #45: fixes #2 login password crash",
                    commit_hash: "a7f8c92"
                }, null, 2);
            }
        } else {
            bodyWrapper.style.display = "none";
        }
    }
}

async function executeApiExplorerRequest() {
    const urlInput = document.getElementById("m3-api-url-input");
    const methodLabel = document.getElementById("m3-api-method-label");
    const bodyInput = document.getElementById("m3-api-body-input");
    const resStatus = document.getElementById("m3-api-res-status");
    const resTime = document.getElementById("m3-api-res-time");
    const resViewer = document.getElementById("m3-api-response-viewer");

    if (!urlInput || !resViewer) return;

    const url = urlInput.value.trim();
    const method = methodLabel?.innerText || "GET";

    // Check if user is testing a binary download endpoint (PDF/CSV)
    if (url.includes("/export/pdf")) {
        exportPdfReport();
        resViewer.innerText = `// File download initiated: GET ${url}\n// Format: application/pdf (Binary Report)`;
        if (resStatus) resStatus.innerText = "200 OK";
        if (resTime) resTime.innerText = "Download triggered";
        return;
    }

    resViewer.innerText = `Sending ${method} ${url}...`;
    const startTime = performance.now();

    try {
        const headers = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const options = { method, headers };
        if (method === "POST") {
            headers["Content-Type"] = "application/json";
            if (bodyInput) options.body = bodyInput.value;
        }

        const response = await fetch(url, options);
        const elapsed = Math.round(performance.now() - startTime);

        if (resTime) resTime.innerText = `${elapsed} ms`;
        if (resStatus) {
            resStatus.innerText = `${response.status} ${response.statusText || 'OK'}`;
            resStatus.className = `badge ${response.ok ? 'badge-low' : 'badge-crit'}`;
        }

        const contentType = response.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
            const json = await response.json();
            resViewer.innerText = JSON.stringify(json, null, 2);
        } else if (contentType.includes("text/csv") || url.includes("/export/csv")) {
            const text = await response.text();
            resViewer.innerText = text;
        } else {
            const text = await response.text();
            resViewer.innerText = text;
        }
    } catch (err) {
        const elapsed = Math.round(performance.now() - startTime);
        if (resTime) resTime.innerText = `${elapsed} ms`;
        if (resStatus) {
            resStatus.innerText = "Network Error";
            resStatus.className = "badge badge-crit";
        }
        resViewer.innerText = `Request Failed: ${err.message}`;
    }
}

// PDF & CSV Export Handlers - Direct browser download
function exportPdfReport() {
    const pId = activeProjectId ? `?project_id=${activeProjectId}` : "";
    window.location.href = `/api/v1/export/pdf${pId}`;
}

function exportCsvReport() {
    const pId = activeProjectId ? `?project_id=${activeProjectId}` : "";
    window.location.href = `/api/v1/export/csv${pId}`;
}
