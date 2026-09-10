from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from typing import Optional
import io
import csv
from datetime import datetime

from app.database import get_db
from app.models.issue import Issue, WorkflowState, IssueSeverity, IssuePriority
from app.models.project import Project

# ReportLab imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

router = APIRouter(prefix="/api/v1/export", tags=["Export"])

@router.get("/pdf")
def export_pdf(
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Issue)
    proj_name = "All Projects"
    if project_id is not None:
        query = query.filter(Issue.project_id == project_id)
        proj = db.query(Project).filter(Project.id == project_id).first()
        if proj:
            proj_name = proj.name

    issues = query.all()
    total_bugs = len(issues)

    resolved_states = [WorkflowState.RESOLVED, WorkflowState.CLOSED]
    resolved_count = sum(1 for i in issues if i.status == WorkflowState.RESOLVED)
    closed_count = sum(1 for i in issues if i.status == WorkflowState.CLOSED)
    fixed_count = resolved_count + closed_count
    open_count = total_bugs - fixed_count

    fix_rate = round((fixed_count / total_bugs) * 100, 1) if total_bugs > 0 else 0.0

    # MTTR calculation
    tot_hours = 0.0
    res_with_time = 0
    for i in issues:
        if i.status in resolved_states:
            h = i.resolution_time_hours
            if h is not None and h >= 0:
                tot_hours += h
                res_with_time += 1
    mttr = round(tot_hours / res_with_time, 1) if res_with_time > 0 else 0.0

    # Defect Leakage
    prod_count = 0
    for i in issues:
        desc = (i.description or "").lower()
        cat = (i.category or "").lower()
        if "environment: production" in desc or "production" in desc or "production" in cat:
            prod_count += 1
    leakage = round((prod_count / total_bugs) * 100, 1) if total_bugs > 0 else 0.0

    # Critical count
    critical_open = sum(1 for i in issues if i.status not in resolved_states and (i.severity in [IssueSeverity.CRITICAL, IssueSeverity.HIGH] or i.priority in [IssuePriority.CRITICAL, IssuePriority.URGENT]))
    penalty = (critical_open * 15) + (open_count * 3)
    health_score = max(0, min(100, 100 - penalty))

    # Build PDF buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=15
    )
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=12,
        spaceAfter=8
    )
    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1e293b')
    )
    header_cell_style = ParagraphStyle(
        'HeaderCellText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#ffffff')
    )

    story = []

    # Title & Header
    story.append(Paragraph("BugFlow - Software Quality Scorecard & Analytics Report", title_style))
    story.append(Paragraph(f"Project: <b>{proj_name}</b> | Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} | Automated CI/CD Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=0, spaceAfter=12))

    # Executive Summary
    story.append(Paragraph("1. Executive Summary & Core Quality Metrics", section_title))
    metrics_data = [
        [
            Paragraph("Metric", header_cell_style),
            Paragraph("Value", header_cell_style),
            Paragraph("Engineering Benchmark", header_cell_style),
            Paragraph("Status", header_cell_style)
        ],
        [
            Paragraph("Fix Rate Percentage", cell_style),
            Paragraph(f"<b>{fix_rate}%</b>", cell_style),
            Paragraph("> 80.0% Target", cell_style),
            Paragraph("PASSED" if fix_rate >= 80 else "REVIEW", cell_style)
        ],
        [
            Paragraph("Mean Time to Resolution (MTTR)", cell_style),
            Paragraph(f"<b>{mttr} hrs</b>", cell_style),
            Paragraph("< 48.0 hrs Target", cell_style),
            Paragraph("HEALTHY" if mttr < 48 else "ELEVATED", cell_style)
        ],
        [
            Paragraph("Defect Leakage Rate (%)", cell_style),
            Paragraph(f"<b>{leakage}%</b>", cell_style),
            Paragraph("< 15.0% Target", cell_style),
            Paragraph("PASSED" if leakage < 15 else "ATTENTION", cell_style)
        ],
        [
            Paragraph("Backlog Health Score", cell_style),
            Paragraph(f"<b>{health_score} / 100</b>", cell_style),
            Paragraph(">= 90 for Release", cell_style),
            Paragraph("READY FOR RELEASE" if health_score >= 90 else "BACKLOG BLOCKED", cell_style)
        ]
    ]

    metrics_table = Table(metrics_data, colWidths=[160, 100, 150, 130])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 14))

    # Defect Distribution
    story.append(Paragraph("2. Defect Volume & Pipeline Breakdown", section_title))
    counts_data = [
        [
            Paragraph("Total Bugs", header_cell_style),
            Paragraph("Open / In-Progress", header_cell_style),
            Paragraph("Resolved / Closed", header_cell_style),
            Paragraph("Critical Open", header_cell_style),
            Paragraph("Production Escapes", header_cell_style)
        ],
        [
            Paragraph(str(total_bugs), cell_style),
            Paragraph(str(open_count), cell_style),
            Paragraph(str(fixed_count), cell_style),
            Paragraph(str(critical_open), cell_style),
            Paragraph(str(prod_count), cell_style)
        ]
    ]
    counts_table = Table(counts_data, colWidths=[108, 108, 108, 108, 108])
    counts_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#475569')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f1f5f9')]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(counts_table)
    story.append(Spacer(1, 14))

    # Recent Critical & High Priority Bugs
    story.append(Paragraph("3. Recent Critical & High Priority Defects", section_title))
    critical_bugs = [
        i for i in issues
        if i.severity in [IssueSeverity.CRITICAL, IssueSeverity.HIGH, IssueSeverity.MAJOR]
           or i.priority in [IssuePriority.CRITICAL, IssuePriority.URGENT, IssuePriority.HIGH]
    ][:10]

    bug_rows = [
        [
            Paragraph("Key", header_cell_style),
            Paragraph("Title", header_cell_style),
            Paragraph("Severity", header_cell_style),
            Paragraph("Status", header_cell_style),
            Paragraph("Resolution Time", header_cell_style),
            Paragraph("Assignee", header_cell_style)
        ]
    ]

    for b in critical_bugs:
        assignee_name = b.assignee.name if b.assignee else "Unassigned"
        st_val = b.status.value if hasattr(b.status, 'value') else str(b.status)
        sev_val = b.severity.value if hasattr(b.severity, 'value') else str(b.severity)
        
        # Calculate individual resolution time
        res_str = "In Progress"
        if b.status in resolved_states:
            h = b.resolution_time_hours
            if h is not None:
                res_str = f"{h} hrs"
            else:
                res_str = "Resolved"

        bug_rows.append([
            Paragraph(f"<b>{b.issue_key}</b>", cell_style),
            Paragraph(b.title[:35] + ("..." if len(b.title) > 35 else ""), cell_style),
            Paragraph(sev_val, cell_style),
            Paragraph(st_val, cell_style),
            Paragraph(f"<b>{res_str}</b>", cell_style),
            Paragraph(assignee_name, cell_style)
        ])

    if len(bug_rows) == 1:
        bug_rows.append([Paragraph("No critical or high severity defects found.", cell_style), "", "", "", "", ""])

    bugs_table = Table(bug_rows, colWidths=[65, 175, 65, 75, 85, 75])
    bugs_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#fca5a5')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#fef2f2')]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(bugs_table)
    story.append(Spacer(1, 14))

    # 4. MTTR Resolution Time & SLA Breakdown
    story.append(Paragraph("4. Mean Time to Resolution (MTTR) & SLA Performance", section_title))
    sla_config = [
        ("CRITICAL", 8.0),
        ("HIGH", 24.0),
        ("MEDIUM", 48.0),
        ("LOW", 72.0)
    ]
    mttr_rows = [
        [
            Paragraph("Priority Level", header_cell_style),
            Paragraph("Target SLA", header_cell_style),
            Paragraph("Average MTTR", header_cell_style),
            Paragraph("Resolved Defects", header_cell_style),
            Paragraph("SLA Compliance", header_cell_style)
        ]
    ]

    for p_name, sla_target in sla_config:
        p_resolved_times = []
        for i in issues:
            if i.status in resolved_states:
                p_val = i.priority.value if hasattr(i.priority, 'value') else str(i.priority).upper()
                norm_p = "CRITICAL" if (p_val in ["CRITICAL", "URGENT"] or i.severity == IssueSeverity.CRITICAL) else ("HIGH" if p_val in ["HIGH", "MAJOR"] else ("LOW" if p_val in ["LOW", "TRIVIAL"] else "MEDIUM"))
                if norm_p == p_name:
                    h = i.resolution_time_hours
                    if h is not None and h >= 0:
                        p_resolved_times.append(h)
        
        if p_resolved_times:
            avg_val = round(sum(p_resolved_times) / len(p_resolved_times), 1)
            sla_status = "PASSED" if avg_val <= sla_target else "ELEVATED"
            mttr_display = f"{avg_val} hrs"
        else:
            avg_val = 0.0
            sla_status = "NO DATA"
            mttr_display = "0.0 hrs"

        mttr_rows.append([
            Paragraph(f"<b>{p_name}</b>", cell_style),
            Paragraph(f"&lt; {sla_target} hrs", cell_style),
            Paragraph(f"<b>{mttr_display}</b>", cell_style),
            Paragraph(str(len(p_resolved_times)), cell_style),
            Paragraph(f"<b>{sla_status}</b>", cell_style)
        ])

    mttr_table = Table(mttr_rows, colWidths=[110, 105, 110, 110, 105])
    mttr_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#a7f3d0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f0fdf4')]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(mttr_table)

    # Build document
    doc.build(story)
    buffer.seek(0)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    filename = f"bugflow_quality_report_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/csv")
def export_csv(
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Issue)
    if project_id is not None:
        query = query.filter(Issue.project_id == project_id)

    issues = query.order_by(Issue.id.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output, lineterminator='\r\n')

    # Headers
    headers = [
        "Issue Key",
        "Title",
        "Type",
        "Status",
        "Priority",
        "Severity",
        "Category",
        "Priority Score",
        "Project ID",
        "Project Name",
        "Reporter",
        "Assignee",
        "Created At",
        "Resolved At",
        "Resolution Time (Hours)",
        "Resolution Time (Formatted)",
        "Description"
    ]
    writer.writerow(headers)

    resolved_states = [WorkflowState.RESOLVED, WorkflowState.CLOSED]

    for i in issues:
        rep_name = i.reporter.name if i.reporter else "None"
        asg_name = i.assignee.name if i.assignee else "Unassigned"
        proj_name = i.project.name if i.project else ""
        c_at = i.created_at.strftime("%Y-%m-%d %H:%M:%S") if i.created_at else ""
        r_at = i.resolved_at.strftime("%Y-%m-%d %H:%M:%S") if i.resolved_at else ""

        # Resolution Time (MTTR) calculation
        res_time_hours = ""
        res_time_formatted = "N/A (Open)"
        if i.status in resolved_states:
            h = i.resolution_time_hours
            if h is not None:
                res_time_hours = h
                res_time_formatted = i.resolution_time_formatted or f"{h} hrs"
            else:
                res_time_formatted = "Resolved"

        writer.writerow([
            i.issue_key,
            i.title,
            i.issue_type.value if hasattr(i.issue_type, 'value') else str(i.issue_type),
            i.status.value if hasattr(i.status, 'value') else str(i.status),
            i.priority.value if hasattr(i.priority, 'value') else str(i.priority),
            i.severity.value if hasattr(i.severity, 'value') else str(i.severity),
            i.category or "General",
            i.priority_score or 0.0,
            i.project_id,
            proj_name,
            rep_name,
            asg_name,
            c_at,
            r_at,
            res_time_hours,
            res_time_formatted,
            (i.description or "").replace("\n", " ")
        ])

    raw_csv = output.getvalue()
    output.close()

    # Prepend UTF-8 BOM so Microsoft Excel and Windows text viewers immediately recognize and open it
    csv_bytes = ("\ufeff" + raw_csv).encode("utf-8")

    filename = f"bugflow_bugs_registry_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
