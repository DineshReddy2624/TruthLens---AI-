"""PDF report generation service using ReportLab."""

import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
import logging

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.verification import (
    VerificationRequest,
    ExtractedClaim,
    VerificationReport,
    VerdictLabel,
)
from app.models.evidence import RetrievedSource, EvidenceRecord
from app.agents.base import run_agent_step

logger = logging.getLogger(__name__)


class ReportAgentOutput(BaseModel):
    executive_summary: str
    overall_assessment: str = "Mixed"

REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "reports"


def get_label_color(label: str) -> colors.Color:
    """Return ReportLab color for standard 5 verdict labels."""
    l = label.lower()
    if "supported" in l and "partially" not in l:
        return colors.HexColor("#16a34a")  # Green
    elif "contradicted" in l:
        return colors.HexColor("#dc2626")  # Red
    elif "partially" in l:
        return colors.HexColor("#d97706")  # Amber
    elif "conflicting" in l:
        return colors.HexColor("#7c3aed")  # Purple
    else:
        return colors.HexColor("#4b5563")  # Gray (Insufficient Evidence)


def generate_pdf_report(
    db: Session,
    request_id: int,
    custom_llm: Any = None,
) -> str:
    """Generate a comprehensive PDF fact-check report and persist to verification_reports."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    pdf_filename = f"report_{request_id}_{int(datetime.now(timezone.utc).timestamp())}.pdf"
    pdf_path = str(REPORTS_DIR / pdf_filename)

    vr = db.query(VerificationRequest).filter_by(id=request_id).first()
    if not vr:
        raise ValueError(f"VerificationRequest {request_id} not found")

    claims = db.query(ExtractedClaim).filter_by(request_id=request_id).all()

    # 1. Generate Executive Summary via LLM
    claims_breakdown_lines = []
    for c in claims:
        lbl = c.result.label.value if c.result and hasattr(c.result.label, "value") else "Insufficient Evidence"
        conf = f"{int((c.result.confidence or 0.5) * 100)}%" if c.result else "N/A"
        claims_breakdown_lines.append(f"- Claim: \"{c.claim_text}\" | Verdict: {lbl} (Confidence: {conf})")

    breakdown_text = "\n".join(claims_breakdown_lines) if claims_breakdown_lines else "No claims extracted."

    user_prompt_content = f"Document/Input Title: {vr.source_url or f'Verification Request #{vr.id}'}\nTotal Claims: {len(claims)}\nClaim Results Breakdown:\n{breakdown_text}"

    try:
        summary_res: ReportAgentOutput = run_agent_step(
            prompt_filename="report_generation.md",
            user_content=user_prompt_content,
            schema_class=ReportAgentOutput,
            db=db,
            request_id=request_id,
            agent_name="Report Generation Agent",
            custom_llm=custom_llm,
        )
        executive_summary = summary_res.executive_summary
    except Exception as e:
        logger.warning(f"Could not generate executive summary via LLM: {e}")
        executive_summary = f"Multi-agent investigation of {len(claims)} claim(s) completed with empirical evidence aggregation."

    # 2. Build ReportLab PDF
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#1e293b"),
    )
    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=15,
    )
    section_h2 = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=14,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
    )
    exec_summary_style = ParagraphStyle(
        "ExecSummary",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor("#1e3a8a"),
    )
    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
    )

    story = []

    # Title & Header
    story.append(Paragraph("TruthLens AI — Fact Verification Report", title_style))
    created_str = vr.created_at.strftime("%Y-%m-%d %H:%M UTC") if vr.created_at else datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story.append(Paragraph(f"Request ID: #{vr.id} &bull; Generated: {created_str} &bull; Pipeline: Multi-Agent NLI + Cross-Encoder Hybrid", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#cbd5e1"), spaceAfter=15))

    # Executive Summary Card
    story.append(Paragraph("Executive Summary", section_h2))
    exec_summary_table = Table(
        [[Paragraph(executive_summary, exec_summary_style)]],
        colWidths=[532],
    )
    exec_summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
        ("BORDER", (0, 0), (-1, -1), 1, colors.HexColor("#bfdbfe")),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(exec_summary_table)
    story.append(Spacer(1, 15))

    # Request Overview Table
    story.append(Paragraph("Verification Overview", section_h2))
    overview_data = [
        [Paragraph("<b>Input Type:</b>", table_cell_style), Paragraph(vr.input_type.value.capitalize(), table_cell_style)],
        [Paragraph("<b>Status:</b>", table_cell_style), Paragraph(vr.status.value.upper(), table_cell_style)],
        [Paragraph("<b>Source URL:</b>", table_cell_style), Paragraph(vr.source_url or "Direct Input / File Upload", table_cell_style)],
        [Paragraph("<b>Total Claims Identified:</b>", table_cell_style), Paragraph(str(len(claims)), table_cell_style)],
    ]
    overview_table = Table(overview_data, colWidths=[160, 372])
    overview_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(overview_table)
    story.append(Spacer(1, 15))

    # Claims & Verdicts Summary Table
    story.append(Paragraph("Claims & Verdicts Summary", section_h2))
    claims_table_data = [
        [
            Paragraph("<b>#</b>", table_cell_style),
            Paragraph("<b>Factual Claim</b>", table_cell_style),
            Paragraph("<b>Verdict</b>", table_cell_style),
            Paragraph("<b>Confidence</b>", table_cell_style),
        ]
    ]

    for idx, c in enumerate(claims, 1):
        lbl = c.result.label.value if c.result and hasattr(c.result.label, "value") else "Insufficient Evidence"
        conf_str = f"{int((c.result.confidence or 0.5) * 100)}%" if c.result else "N/A"
        badge_color = get_label_color(lbl)
        badge_style = ParagraphStyle(
            f"Badge_{idx}",
            parent=table_cell_style,
            fontName="Helvetica-Bold",
            textColor=badge_color,
        )
        claims_table_data.append([
            Paragraph(str(idx), table_cell_style),
            Paragraph(c.claim_text, table_cell_style),
            Paragraph(lbl, badge_style),
            Paragraph(conf_str, table_cell_style),
        ])

    claims_summary_table = Table(claims_table_data, colWidths=[25, 335, 120, 52])
    claims_summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(claims_summary_table)
    story.append(Spacer(1, 20))

    # Detailed Claims & Evidence Section
    story.append(Paragraph("Detailed Evidence & Claim Analysis", section_h2))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=10))

    for idx, c in enumerate(claims, 1):
        lbl = c.result.label.value if c.result and hasattr(c.result.label, "value") else "Insufficient Evidence"
        conf_str = f"{int((c.result.confidence or 0.5) * 100)}%" if c.result else "N/A"
        lbl_color = get_label_color(lbl)

        claim_header_style = ParagraphStyle(
            f"ClaimH_{idx}",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#0f172a"),
        )

        claim_elements = []
        claim_elements.append(Paragraph(f"Claim #{idx}: {c.claim_text}", claim_header_style))

        # Verdict info line
        verdict_line_style = ParagraphStyle(
            f"VLine_{idx}",
            parent=body_style,
            fontName="Helvetica-Bold",
            textColor=lbl_color,
        )
        claim_elements.append(Paragraph(f"Verdict: {lbl} &bull; Confidence: {conf_str} &bull; Type: {c.claim_type or 'General'}", verdict_line_style))
        claim_elements.append(Spacer(1, 4))

        # Explanation
        if c.result and c.result.explanation:
            claim_elements.append(Paragraph(f"<b>AI Explanation:</b> {c.result.explanation}", body_style))
            claim_elements.append(Spacer(1, 4))

        if c.result and c.result.missing_context:
            claim_elements.append(Paragraph(f"<b>Missing Context:</b> {c.result.missing_context}", body_style))
            claim_elements.append(Spacer(1, 4))

        # Evidence Passages
        if c.evidence_records:
            claim_elements.append(Paragraph("<b>Retrieved Evidence Passages:</b>", table_cell_style))
            ev_data = []
            for p_idx, ev in enumerate(c.evidence_records[:4], 1):
                src = db.query(RetrievedSource).filter_by(id=ev.source_id).first()
                domain_title = f"{src.domain or 'Web'} - {src.title or src.url}" if src else "Evidence Source"
                nli_tag = f"[{ev.nli_label.upper()}]" if ev.nli_label else ""
                passage_cell = f"<b>[{p_idx}] {domain_title} {nli_tag}:</b><br/>\"{ev.passage[:280]}...\""
                ev_data.append([Paragraph(passage_cell, table_cell_style)])

            ev_table = Table(ev_data, colWidths=[532])
            ev_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fafafa")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f3f4f6")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            claim_elements.append(ev_table)

        claim_elements.append(Spacer(1, 14))
        story.append(KeepTogether(claim_elements))

    # Build Document
    doc.build(story)

    # 3. Persist to MySQL verification_reports
    existing_report = db.query(VerificationReport).filter_by(request_id=request_id).first()
    if existing_report:
        existing_report.pdf_path = pdf_path
        existing_report.summary = executive_summary
        db.add(existing_report)
    else:
        new_report = VerificationReport(
            request_id=request_id,
            pdf_path=pdf_path,
            summary=executive_summary,
        )
        db.add(new_report)

    db.commit()
    return pdf_path
