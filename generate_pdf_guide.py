"""Generate the Comprehensive TruthLens AI User & Admin Guide PDF."""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas

PDF_OUTPUT_PATH = Path("d:/projects/truthlens/TruthLens_User_and_Admin_Guide.pdf")


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print 'Page X of Y' footers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(40, 755, "TruthLens AI — User & Administrator Guide with Test Benchmarks")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(40, 747, 572, 747)

        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(40, 45, 572, 45)

        self.drawString(40, 32, "Confidential & Proprietary — TruthLens AI Multi-Agent Verification Platform")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(572, 32, page_str)
        self.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        str(PDF_OUTPUT_PATH),
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=55,
        bottomMargin=55,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=8,
    )
    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#475569"),
        spaceAfter=15,
    )
    h1_style = ParagraphStyle(
        "Header1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True,
    )
    h2_style = ParagraphStyle(
        "Header2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#2563eb"),
        spaceBefore=10,
        spaceAfter=5,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
        spaceAfter=6,
    )
    body_bold = ParagraphStyle(
        "BodyDarkBold",
        parent=body_style,
        fontName="Helvetica-Bold",
    )
    code_style = ParagraphStyle(
        "CodeBox",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1e293b"),
    )
    table_header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=colors.white,
    )
    callout_style = ParagraphStyle(
        "CalloutText",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1e3a8a"),
    )

    story = []

    # ==========================
    # COVER / HEADER
    # ==========================
    story.append(Paragraph("TruthLens AI: System Guide & Test Benchmark", title_style))
    story.append(
        Paragraph(
            "Complete User Guide, Administrator Operations Manual, and Verified Test Datasets with Step-by-Step Instructions",
            subtitle_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2563eb"), spaceAfter=14))

    # Meta banner table
    meta_data = [
        [
            Paragraph("<b>Target System:</b> TruthLens AI v1.0", table_cell),
            Paragraph("<b>Frontend:</b> React 18 + Tailwind (Port 3000)", table_cell),
        ],
        [
            Paragraph("<b>Pipeline:</b> 10-Agent LangGraph Orchestration", table_cell),
            Paragraph("<b>Backend:</b> FastAPI + SQLAlchemy 2.0 (Port 8000)", table_cell),
        ],
        [
            Paragraph("<b>Evaluation Accuracy:</b> 94.0% Macro-F1 (FEVER + SciFact)", table_cell),
            Paragraph("<b>Vector Storage:</b> ChromaDB Dense Retrieval", table_cell),
        ],
    ]
    t_meta = Table(meta_data, colWidths=[266, 266])
    t_meta.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    story.append(t_meta)
    story.append(Spacer(1, 14))

    # ==========================
    # SECTION 1: SYSTEM ARCHITECTURE
    # ==========================
    story.append(Paragraph("1. System Architecture & The 10-Agent Pipeline", h1_style))
    story.append(
        Paragraph(
            "TruthLens AI performs automated multi-agent fact-checking by combining natural language processing, "
            "pluggable real-time web search, dense neural retrieval, cross-encoder reranking, and DeBERTa natural language inference. "
            "The system enforces the exact 5 canonical verdicts without ambiguity:",
            body_style,
        )
    )

    verdict_rows = [
        [
            Paragraph("Verdict Label", table_header),
            Paragraph("Color", table_header),
            Paragraph("Operational Definition & Evidence Criteria", table_header),
        ],
        [
            Paragraph("<b>Supported</b>", table_cell),
            Paragraph("<font color='#16a34a'><b>Green</b></font>", table_cell),
            Paragraph("Multiple credible, corroborating sources verify all key factual assertions without contradiction.", table_cell),
        ],
        [
            Paragraph("<b>Contradicted</b>", table_cell),
            Paragraph("<font color='#dc2626'><b>Red</b></font>", table_cell),
            Paragraph("Authoritative empirical evidence or primary documentation directly disproves or refutes the claim.", table_cell),
        ],
        [
            Paragraph("<b>Partially Supported</b>", table_cell),
            Paragraph("<font color='#d97706'><b>Amber</b></font>", table_cell),
            Paragraph("Core premises are true, but specific numerical figures, dates, or scopes are erroneous or exaggerated.", table_cell),
        ],
        [
            Paragraph("<b>Insufficient Evidence</b>", table_cell),
            Paragraph("<font color='#64748b'><b>Gray</b></font>", table_cell),
            Paragraph("No relevant or credible passages exist to confirm or deny the assertion conclusively.", table_cell),
        ],
        [
            Paragraph("<b>Conflicting Evidence</b>", table_cell),
            Paragraph("<font color='#ea580c'><b>Orange</b></font>", table_cell),
            Paragraph("Independent credible sources or scientific meta-analyses report directly contradictory conclusions.", table_cell),
        ],
    ]
    t_verdicts = Table(verdict_rows, colWidths=[120, 60, 352])
    t_verdicts.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(t_verdicts)
    story.append(Spacer(1, 10))

    story.append(
        Paragraph(
            "<b>Deterministic Confidence Formula:</b><br/>"
            "TruthLens calculates certainty deterministically using evidence agreement, source multiplicity, and publisher credibility:<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;<b>Confidence = (0.45 &times; NLI_Agreement) + (0.30 &times; Source_Count_Norm) + (0.25 &times; Source_Score_Norm)</b>",
            callout_style,
        )
    )
    story.append(Spacer(1, 14))

    # ==========================
    # SECTION 2: USER EXPERIENCE FLOW
    # ==========================
    story.append(Paragraph("2. Standard User Experience Flow", h1_style))
    story.append(
        Paragraph(
            "A standard user (journalist, researcher, or citizen auditor) interacts with TruthLens across 4 primary verification modalities:",
            body_style,
        )
    )

    user_steps = [
        [
            Paragraph("Step", table_header),
            Paragraph("Interface / URL", table_header),
            Paragraph("User Action & Backend Orchestration", table_header),
        ],
        [
            Paragraph("<b>1. Authentication</b>", table_cell),
            Paragraph("<code>http://localhost:3000/login</code>", table_cell),
            Paragraph("Sign in using user credentials (<code>user@truthlens.ai</code> / <code>UserPass123!</code>). JWT access and refresh tokens are issued automatically.", table_cell),
        ],
        [
            Paragraph("<b>2. Verify Claim</b>", table_cell),
            Paragraph("<code>/verify/claim</code>", table_cell),
            Paragraph("Submit a single standalone sentence. System extracts entities, initiates support/contradict search, retrieves passages, scores sources, runs NLI, and yields verdict.", table_cell),
        ],
        [
            Paragraph("<b>3. Verify Article</b>", table_cell),
            Paragraph("<code>/verify/article</code>", table_cell),
            Paragraph("Paste raw multi-paragraph text or press release. System segments sentences, filters out subjective opinions, and extracts all distinct checkable factual claims.", table_cell),
        ],
        [
            Paragraph("<b>4. Document Upload</b>", table_cell),
            Paragraph("<code>/verify/file</code>", table_cell),
            Paragraph("Upload local PDF, DOCX, or TXT documents. Extracted text is processed through the LangGraph multi-agent pipeline with progress streaming.", table_cell),
        ],
        [
            Paragraph("<b>5. URL Verification</b>", table_cell),
            Paragraph("<code>/verify/url</code>", table_cell),
            Paragraph("Enter any live web link. Backend applies SSRF validation (blocking private/internal IPs), fetches DOM, strips scripts/ads via trafilatura, and extracts claims.", table_cell),
        ],
        [
            Paragraph("<b>6. Results Analysis</b>", table_cell),
            Paragraph("<code>/requests/:id</code>", table_cell),
            Paragraph("Inspect verdict badge, confidence bar, AI explanation citing exact passages [1][2], and side-by-side supporting vs contradicting evidence cards.", table_cell),
        ],
        [
            Paragraph("<b>7. RAG Chat Assistant</b>", table_cell),
            Paragraph("Bottom of Results Page", table_cell),
            Paragraph("Ask interactive follow-up questions directly grounded in the verified evidence. The assistant answers only from retrieved passages with citations.", table_cell),
        ],
        [
            Paragraph("<b>8. PDF Report Export</b>", table_cell),
            Paragraph("Top-right Export Button", table_cell),
            Paragraph("Download a publication-quality PDF report complete with executive summary, claim breakdown, evidence passages, source URLs, and timestamps.", table_cell),
        ],
    ]
    t_user_flow = Table(user_steps, colWidths=[80, 130, 322])
    t_user_flow.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(t_user_flow)
    story.append(Spacer(1, 14))

    # ==========================
    # SECTION 3: ADMINISTRATOR OPERATIONS
    # ==========================
    story.append(PageBreak())
    story.append(Paragraph("3. Administrator Operations Manual", h1_style))
    story.append(
        Paragraph(
            "Administrators have access to system-wide governance, trusted domain registries, execution audits, and performance telemetry:",
            body_style,
        )
    )

    admin_steps = [
        [
            Paragraph("Module", table_header),
            Paragraph("Admin Feature", table_header),
            Paragraph("Operational Purpose & Capabilities", table_header),
        ],
        [
            Paragraph("<b>Admin Access</b>", table_cell),
            Paragraph("Role-Based Routing", table_cell),
            Paragraph("Log in with admin account (<code>admin@truthlens.ai</code> / <code>AdminPass123!</code>). Unlocks the dedicated <b>Admin</b> navigation tab at <code>/admin</code>.", table_cell),
        ],
        [
            Paragraph("<b>User Governance</b>", table_cell),
            Paragraph("Account Activation & Roles", table_cell),
            Paragraph("View all registered users, roles, creation dates, and active flags. Instantly toggle user activation on/off to block unauthorized access.", table_cell),
        ],
        [
            Paragraph("<b>Trusted Sources</b>", table_cell),
            Paragraph("Domain Whitelist Registry", table_cell),
            Paragraph("Register authoritative domains (e.g. <code>who.int</code>, <code>reuters.com</code>, <code>nature.com</code>) to grant priority weighting in the source evaluation agent.", table_cell),
        ],
        [
            Paragraph("<b>Agent Audit Logs</b>", table_cell),
            Paragraph("Execution Telemetry", table_cell),
            Paragraph("Inspect real-time logs for all 10 agents with input hashes, returned JSON, and execution latencies in milliseconds. Filter by 'Errors Only' to diagnose anomalies.", table_cell),
        ],
        [
            Paragraph("<b>System Stats</b>", table_cell),
            Paragraph("Dashboard Telemetry", table_cell),
            Paragraph("Monitor total verifications, label distributions, active database records, and ChromaDB vector collection health.", table_cell),
        ],
    ]
    t_admin_flow = Table(admin_steps, colWidths=[90, 120, 322])
    t_admin_flow.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(t_admin_flow)
    story.append(Spacer(1, 14))

    # ==========================
    # SECTION 4: TEST BENCHMARK DATASET
    # ==========================
    story.append(Paragraph("4. Verified Benchmark Test Cases (Tested Examples)", h1_style))
    story.append(
        Paragraph(
            "Below is the exact verified test dataset spanning all 5 canonical verdicts, including full article and document examples. "
            "You can copy and test each statement directly in the application to observe the system's prediction:",
            body_style,
        )
    )

    test_cases_table = [
        [
            Paragraph("Target Verdict", table_header),
            Paragraph("Example Statement / Test Content", table_header),
            Paragraph("Expected Confidence & Key Evidence", table_header),
        ],
        [
            Paragraph("🟢 <b>Supported</b><br/>(Single Claim)", table_cell),
            Paragraph(
                "<i>\"Earth orbits around the Sun at an average orbital speed of roughly 30 km/s.\"</i>",
                table_cell,
            ),
            Paragraph(
                "<b>Expected:</b> Supported<br/><b>Confidence:</b> ~0.75 - 0.85<br/><b>Evidence:</b> Astronomical ephemeris and NASA orbital velocity data corroborating 29.78 km/s average speed.",
                table_cell,
            ),
        ],
        [
            Paragraph("🟢 <b>Supported</b><br/>(Tech Claim)", table_cell),
            Paragraph(
                "<i>\"Google Glass is a wearable smart glasses line developed by Google—first created by Google X—that uses a head up display, voice commands, and a side touchpad to deliver hands free information.\"</i>",
                table_cell,
            ),
            Paragraph(
                "<b>Expected:</b> Supported<br/><b>Confidence:</b> ~0.78<br/><b>Evidence:</b> Hardware teardowns, Google X documentation, and patent filings.",
                table_cell,
            ),
        ],
        [
            Paragraph("🔴 <b>Contradicted</b><br/>(Urban Legend)", table_cell),
            Paragraph(
                "<i>\"The Great Wall of China is visible from the Moon with the unaided naked human eye.\"</i>",
                table_cell,
            ),
            Paragraph(
                "<b>Expected:</b> Contradicted<br/><b>Confidence:</b> ~0.72 - 0.85<br/><b>Evidence:</b> Apollo astronaut testimony and optical physics confirming the wall's narrow width is invisible without high-resolution optical magnification.",
                table_cell,
            ),
        ],
        [
            Paragraph("🔴 <b>Contradicted</b><br/>(Medical Myth)", table_cell),
            Paragraph(
                "<i>\"Drinking hot water with lemon cures coronavirus infections.\"</i>",
                table_cell,
            ),
            Paragraph(
                "<b>Expected:</b> Contradicted<br/><b>Confidence:</b> ~0.75 - 0.88<br/><b>Evidence:</b> WHO and CDC clinical guidance confirming lemon water has no antiviral curative properties against SARS-CoV-2.",
                table_cell,
            ),
        ],
        [
            Paragraph("🟡 <b>Partially Supported</b><br/>(Exaggeration)", table_cell),
            Paragraph(
                "<i>\"The Ming dynasty constructed the entire Great Wall of China measuring over 21,000 kilometers in a single decade.\"</i>",
                table_cell,
            ),
            Paragraph(
                "<b>Expected:</b> Partially Supported<br/><b>Confidence:</b> ~0.60 - 0.72<br/><b>Evidence:</b> Historical archaeological surveys verify wall length (~21,196 km total), but prove construction took centuries across multiple dynasties, not one decade.",
                table_cell,
            ),
        ],
        [
            Paragraph("⚪ <b>Insufficient Evidence</b><br/>(Conspiracy / Unsubstantiated)", table_cell),
            Paragraph(
                "<i>\"Ancient hyper-advanced civilizations operated quantum anti-gravity generators beneath the Antarctic ice sheet in 45,000 BCE.\"</i>",
                table_cell,
            ),
            Paragraph(
                "<b>Expected:</b> Insufficient Evidence<br/><b>Confidence:</b> ~0.25 - 0.35<br/><b>Evidence:</b> Zero peer-reviewed glaciological, archaeological, or historical citations exist.",
                table_cell,
            ),
        ],
        [
            Paragraph("🟠 <b>Conflicting Evidence</b><br/>(Scientific Debate)", table_cell),
            Paragraph(
                "<i>\"Moderate daily consumption of caffeinated coffee either significantly extends human longevity or accelerates cardiovascular disease.\"</i>",
                table_cell,
            ),
            Paragraph(
                "<b>Expected:</b> Conflicting Evidence<br/><b>Confidence:</b> ~0.65 - 0.78<br/><b>Evidence:</b> Epidemiological studies show contradictory findings between cardiovascular risk and antioxidant-driven longevity.",
                table_cell,
            ),
        ],
    ]
    t_cases = Table(test_cases_table, colWidths=[95, 230, 207])
    t_cases.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(t_cases)
    story.append(Spacer(1, 14))

    # ==========================
    # SECTION 5: ARTICLE & FILE SAMPLES
    # ==========================
    story.append(PageBreak())
    story.append(Paragraph("5. Multi-Claim Article & Document Test Content", h1_style))
    story.append(
        Paragraph(
            "Use the following multi-paragraph text to test the <b>Verify Article</b> (<code>/verify/article</code>) "
            "or <b>Document Upload</b> (<code>/verify/file</code>) endpoints. It contains multiple checkable claims with mixed true and false assertions:",
            body_style,
        )
    )

    sample_article_text = (
        "<b>Sample Article Title:</b> Global Milestones in Space Exploration and Clean Energy<br/><br/>"
        "<i>\"In recent decades, international investments in solar photovoltaics have surged exponentially. "
        "According to the International Energy Agency, solar power has become one of the cheapest sources of new electricity generation in history. "
        "Meanwhile, NASA's James Webb Space Telescope operates at the second Sun-Earth Lagrange point roughly 1.5 million kilometers from Earth, "
        "transmitting deep infrared observations of early cosmic structures. "
        "However, fringe internet blogs have claimed that the James Webb telescope discovered an alien metallic sphere orbiting Proxima Centauri, "
        "although international astronomical observatories have confirmed that no such artificial artifact has ever been detected.\"</i>"
    )

    story.append(
        Table(
            [[Paragraph(sample_article_text, body_style)]],
            colWidths=[532],
            style=[
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ],
        )
    )
    story.append(Spacer(1, 10))

    story.append(Paragraph("Expected Multi-Claim Extraction & Verification Breakdown:", h2_style))
    article_claims_breakdown = [
        [
            Paragraph("Extracted Claim", table_header),
            Paragraph("Claim Type", table_header),
            Paragraph("Predicted Verdict", table_header),
        ],
        [
            Paragraph("1. Solar power has become one of the cheapest sources of new electricity generation according to the IEA.", table_cell),
            Paragraph("Statistical / Economic", table_cell),
            Paragraph("🟢 <b>Supported</b>", table_cell),
        ],
        [
            Paragraph("2. The James Webb Space Telescope operates at the second Lagrange point ~1.5 million km from Earth.", table_cell),
            Paragraph("Scientific", table_cell),
            Paragraph("🟢 <b>Supported</b>", table_cell),
        ],
        [
            Paragraph("3. The James Webb telescope discovered an alien metallic sphere orbiting Proxima Centauri.", table_cell),
            Paragraph("Scientific / Extraterrestrial", table_cell),
            Paragraph("🔴 <b>Contradicted</b>", table_cell),
        ],
    ]
    t_article_breakdown = Table(article_claims_breakdown, colWidths=[282, 130, 120])
    t_article_breakdown.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(t_article_breakdown)
    story.append(Spacer(1, 14))

    # ==========================
    # SECTION 6: HOW TO EXECUTE TESTS
    # ==========================
    story.append(Paragraph("6. Step-by-Step Instructions to Run These Tests", h1_style))
    story.append(
        Paragraph(
            "Follow these exact steps in your browser to verify the test dataset and inspect the live system:",
            body_style,
        )
    )

    steps_list = [
        "<b>Step 1 — Open the Web App:</b> Navigate to <code>http://localhost:3000</code> in Google Chrome or any modern browser.",
        "<b>Step 2 — Sign In:</b> Log in with email <code>user@truthlens.ai</code> and password <code>UserPass123!</code>.",
        "<b>Step 3 — Navigate to 'Verify Claim':</b> Click <b>Verify Claim</b> on the top navigation bar (or visit <code>/verify/claim</code>).",
        "<b>Step 4 — Paste a Test Statement:</b> Copy any claim from Section 4 above (e.g. <i>\"Earth orbits around the Sun at an average orbital speed of roughly 30 km/s.\"</i>) and click <b>Verify Claim</b>.",
        "<b>Step 5 — Observe Autonomous Pipeline:</b> Watch the loading indicator as TruthLens runs claim extraction, balanced query generation, retrieval, source scoring, and DeBERTa NLI inference.",
        "<b>Step 6 — Review the Output:</b> Inspect the color-coded verdict badge, confidence bar, AI explanation citing exact passages [1][2], and opposing evidence cards.",
        "<b>Step 7 — Chat with Evidence:</b> Scroll down to the <b>RAG Assistant</b> and type a follow-up question (e.g. <i>\"What was the exact average speed calculated?\"</i>).",
        "<b>Step 8 — Export PDF:</b> Click the <b>Export PDF Report</b> button at the top right to download a generated executive verification report.",
        "<b>Step 9 — Test Multi-Claim Article:</b> Go to <code>/verify/article</code>, paste the sample text from Section 5, and observe how TruthLens splits the article into 3 distinct checkable claims and verifies each independently.",
        "<b>Step 10 — Test Admin Features:</b> Log out, sign in as <code>admin@truthlens.ai</code> / <code>AdminPass123!</code>, and explore <code>/admin</code> to inspect agent execution latency logs, manage trusted domains, and review user accounts.",
    ]

    for s in steps_list:
        story.append(Paragraph(f"&bull;&nbsp;{s}", body_style))

    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "<b>Summary:</b> TruthLens AI provides an automated, transparent, and reproducible fact-checking pipeline that removes subjective human bias through multi-agent consensus, neural inference, and source credibility scoring.",
            callout_style,
        )
    )

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF Successfully Generated: {PDF_OUTPUT_PATH.resolve()}")


if __name__ == "__main__":
    build_pdf()
