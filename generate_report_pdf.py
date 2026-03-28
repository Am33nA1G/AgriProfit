"""
AgriProfit Project Report - PDF Generator
Generates a complete FISAT-style mini project report using reportlab.

Usage:
    python generate_report_pdf.py
Output:
    AgriProfit_Report.pdf
"""
import sys
import os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, Image, KeepTogether, Preformatted,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ──────────────────────────────────────────
# PATHS
# ──────────────────────────────────────────
REPO_ROOT   = Path(__file__).parent
SS_DIR      = REPO_ROOT / "report_screenshots"
LOGO_PATH   = SS_DIR / "fisat_logo.jpg"
OUTPUT_PDF  = REPO_ROOT / "AgriProfit_Report_v2.pdf"

# ──────────────────────────────────────────
# COLOURS
# ──────────────────────────────────────────
DARK_BLUE   = colors.HexColor("#003580")
HEADER_GREY = colors.HexColor("#F2F2F2")
CODE_BG     = colors.HexColor("#F7F7F7")
CODE_BORDER = colors.HexColor("#CCCCCC")
TABLE_HEAD  = colors.HexColor("#1A3A6B")
ALT_ROW     = colors.HexColor("#EEF2FF")

# ──────────────────────────────────────────
# STYLES
# ──────────────────────────────────────────
styles = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, **kw)

TITLE_STYLE = S("ReportTitle",
    fontSize=16, fontName="Times-Bold",
    alignment=TA_CENTER, spaceAfter=8, leading=22)

SUBTITLE_STYLE = S("Subtitle",
    fontSize=11, fontName="Times-Italic",
    alignment=TA_CENTER, spaceAfter=6, leading=16)

SECTION_STYLE = S("SectionHead",
    fontSize=13, fontName="Times-Bold",
    spaceBefore=16, spaceAfter=6, leading=18,
    textColor=DARK_BLUE)

SUBSEC_STYLE = S("SubsecHead",
    fontSize=11, fontName="Times-Bold",
    spaceBefore=10, spaceAfter=4, leading=15)

BODY_STYLE = S("Body",
    fontSize=11, fontName="Times-Roman",
    alignment=TA_JUSTIFY, spaceAfter=6, leading=16)

BODY_CENTRE = S("BodyC",
    fontSize=11, fontName="Times-Roman",
    alignment=TA_CENTER, spaceAfter=6, leading=16)

CHAPTER_TITLE = S("ChapterTitle",
    fontSize=16, fontName="Times-Bold",
    alignment=TA_CENTER, spaceBefore=0, spaceAfter=20, leading=22,
    textColor=DARK_BLUE)

CHAPTER_LABEL = S("ChapterLabel",
    fontSize=13, fontName="Times-Bold",
    alignment=TA_CENTER, spaceBefore=0, spaceAfter=4, leading=18)

BOLD_BODY = S("BoldBody",
    fontSize=11, fontName="Times-Bold",
    alignment=TA_LEFT, spaceAfter=4, leading=16)

CODE_STYLE = S("Code",
    fontSize=8.5, fontName="Courier",
    alignment=TA_LEFT, spaceAfter=4, leading=11,
    backColor=CODE_BG, borderPadding=(6, 6, 6, 8),
    leftIndent=10, rightIndent=10)

CAPTION_STYLE = S("Caption",
    fontSize=9, fontName="Times-Italic",
    alignment=TA_CENTER, spaceAfter=10, leading=12)

BULLET_STYLE = S("Bullet",
    fontSize=11, fontName="Times-Roman",
    alignment=TA_LEFT, spaceAfter=4, leading=16,
    bulletIndent=12, leftIndent=24)

ENUM_STYLE = S("Enum",
    fontSize=11, fontName="Times-Roman",
    alignment=TA_JUSTIFY, spaceAfter=4, leading=16,
    bulletIndent=12, leftIndent=28)

# ──────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────
def chapter(num, title, story):
    story.append(PageBreak())
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(f"Chapter {num}", CHAPTER_LABEL))
    story.append(Paragraph(title, CHAPTER_TITLE))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE))
    story.append(Spacer(1, 0.15*inch))

def section(title, story):
    story.append(Paragraph(title, SECTION_STYLE))

def subsection(title, story):
    story.append(Paragraph(title, SUBSEC_STYLE))

def body(text, story, style=BODY_STYLE):
    story.append(Paragraph(text, style))

def bullet(items, story):
    for item in items:
        story.append(Paragraph(f"\u2022\u00a0\u00a0{item}", BULLET_STYLE))

def enum(items, story, start=1):
    for i, item in enumerate(items, start=start):
        story.append(Paragraph(f"{i}.\u00a0\u00a0{item}", ENUM_STYLE))

def space(story, h=0.1):
    story.append(Spacer(1, h*inch))

def code_block(text, story, caption=""):
    story.append(Spacer(1, 0.05*inch))
    lines = text.strip().split("\n")
    code_text = "\n".join(lines)
    story.append(Preformatted(code_text, CODE_STYLE))
    if caption:
        story.append(Paragraph(f"<i>Listing: {caption}</i>", CAPTION_STYLE))
    story.append(Spacer(1, 0.05*inch))

def data_table(headers, rows, story, caption="", col_widths=None):
    data = [headers] + rows
    if col_widths is None:
        col_widths = [6.2*inch / len(headers)] * len(headers)
    t = Table(data, colWidths=col_widths)
    ts = TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), TABLE_HEAD),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "Times-Bold"),
        ("FONTSIZE",      (0,0), (-1,0), 9),
        ("ALIGN",         (0,0), (-1,-1), "LEFT"),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("FONTNAME",      (0,1), (-1,-1), "Times-Roman"),
        ("FONTSIZE",      (0,1), (-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, ALT_ROW]),
        ("GRID",          (0,0), (-1,-1), 0.4, colors.grey),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("RIGHTPADDING",  (0,0), (-1,-1), 5),
    ])
    t.setStyle(ts)
    story.append(t)
    if caption:
        story.append(Paragraph(f"<i>Table: {caption}</i>", CAPTION_STYLE))
    story.append(Spacer(1, 0.08*inch))

def add_image(path, story, caption="", width=5.5*inch, max_height=7.0*inch):
    p = Path(path)
    if p.exists():
        from reportlab.lib.utils import ImageReader
        try:
            ir = ImageReader(str(p))
            iw, ih = ir.getSize()
            height = width * ih / iw if iw > 0 else width * 0.75
        except Exception:
            height = width * 0.75
        # Scale down if image is taller than the page allows
        if height > max_height:
            scale = max_height / height
            width = width * scale
            height = max_height
        img = Image(str(p), width=width, height=height)
        story.append(img)
        if caption:
            story.append(Paragraph(f"<i>Figure: {caption}</i>", CAPTION_STYLE))
        story.append(Spacer(1, 0.08*inch))
    else:
        story.append(Paragraph(f"[Image not found: {p.name}]", CAPTION_STYLE))

# ──────────────────────────────────────────
# HEADER / FOOTER
# ──────────────────────────────────────────
PROJECT_TITLE = "AgriProfit: An ML-Driven Agricultural Price Forecasting and Advisory Platform"
DEPT_LABEL    = "Computer Science & Engineering \u2014 FISAT"

def on_page(canvas, doc):
    canvas.saveState()
    w, h = A4
    # Header
    canvas.setFont("Times-Italic", 8)
    canvas.setFillColor(colors.HexColor("#444444"))
    canvas.drawString(1.25*inch, h - 0.55*inch, PROJECT_TITLE)
    canvas.drawRightString(w - inch, h - 0.55*inch, DEPT_LABEL)
    canvas.setStrokeColor(colors.HexColor("#AAAAAA"))
    canvas.setLineWidth(0.4)
    canvas.line(1.25*inch, h - 0.65*inch, w - inch, h - 0.65*inch)
    # Footer
    canvas.setFont("Times-Roman", 9)
    canvas.setFillColor(colors.black)
    canvas.drawCentredString(w/2, 0.5*inch, str(canvas.getPageNumber()))
    canvas.restoreState()

def on_first_page(canvas, doc):
    pass  # no header/footer on title page

# ──────────────────────────────────────────
# BUILD STORY
# ──────────────────────────────────────────
def build_story():
    story = []
    W = 6.2 * inch  # usable width

    # ── TITLE PAGE ──
    story.append(Spacer(1, 0.6*inch))
    story.append(Paragraph("AgriProfit: An ML-Driven Agricultural Price", TITLE_STYLE))
    story.append(Paragraph("Forecasting and Advisory Platform", TITLE_STYLE))
    space(story, 0.4)
    story.append(Paragraph(
        "<i>Mini project report submitted in partial fulfilment of the requirements for<br/>"
        "the award of the degree of</i>", SUBTITLE_STYLE))
    space(story, 0.5)
    story.append(Paragraph("<b>Bachelor of Technology</b>", BODY_CENTRE))
    story.append(Paragraph("<i>in</i>", BODY_CENTRE))
    story.append(Paragraph("<b>Computer Science &amp; Engineering</b>", BODY_CENTRE))
    space(story, 0.7)
    story.append(Paragraph("Submitted by", BODY_CENTRE))
    space(story, 0.2)
    for name in ["Abhinav K Manoj", "Adhwai Shyjith", "AdithyaKrishna JG", "Al Ameen AK"]:
        story.append(Paragraph(name, BODY_CENTRE))
    space(story, 0.6)
    if LOGO_PATH.exists():
        img = Image(str(LOGO_PATH), width=1.8*inch, height=1.8*inch)
        img.hAlign = "CENTER"
        story.append(img)
    story.append(Paragraph("<b>Focus on Excellence</b>", BODY_CENTRE))
    space(story, 0.5)
    story.append(Paragraph(
        "<b>Federal Institute of Science And Technology (FISAT)\u00ae</b>", BODY_CENTRE))
    story.append(Paragraph("Angamaly, Ernakulam", BODY_CENTRE))
    space(story, 0.2)
    story.append(Paragraph("<i>Affiliated to</i>", BODY_CENTRE))
    story.append(Paragraph("<b>APJ Abdul Kalam Technological University</b>", BODY_CENTRE))
    story.append(Paragraph("CET Campus, Thiruvananthapuram", BODY_CENTRE))
    story.append(Paragraph("May 2026", BODY_CENTRE))
    story.append(PageBreak())

    # ── CERTIFICATE ──
    space(story, 0.3)
    story.append(Paragraph("FEDERAL INSTITUTE OF SCIENCE AND TECHNOLOGY (FISAT)",
                            CHAPTER_TITLE))
    story.append(Paragraph("Mookkannoor(P.O), Angamaly-683577", BODY_CENTRE))
    space(story, 0.2)
    if LOGO_PATH.exists():
        img2 = Image(str(LOGO_PATH), width=1.5*inch, height=1.5*inch)
        img2.hAlign = "CENTER"
        story.append(img2)
    story.append(Paragraph("<b>Focus on Excellence</b>", BODY_CENTRE))
    space(story, 0.6)
    story.append(Paragraph("CERTIFICATE", CHAPTER_TITLE))
    space(story, 0.5)
    cert_text = (
        'This is to certify that the Mini project report for the project entitled '
        '<b>"AgriProfit: An ML-Driven Agricultural Price Forecasting and Advisory Platform"</b> '
        'is a bonafide report of the project presented during VI<super>th</super> semester '
        '(CSD334 - Mini Project) by <b>Abhinav K Manoj (FITCS22002)</b>, '
        '<b>Adhwai Shyjith (FITCS22013)</b>, <b>AdithyaKrishna JG (FITCS22017)</b>, '
        'and <b>Al Ameen AK (FITCS22018)</b>, in partial fulfilment of the requirements '
        'for the award of the degree of Bachelor of Technology (B.Tech) in Computer Science '
        '&amp; Engineering during the academic year 2025\u201326.'
    )
    body(cert_text, story)
    space(story, 1.5)
    sig_data = [
        ["Project Coordinator", "Project Guide", "Head of the Department"],
        ["Al Ameen AK", "Dr. Neenu Johnson", "Dr. Paul P Mathai"],
    ]
    sig_table = Table(sig_data, colWidths=[W/3]*3)
    sig_table.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (-1,-1), "Times-Roman"),
        ("FONTSIZE",  (0,0), (-1,-1), 10),
        ("FONTNAME",  (0,1), (-1,1), "Times-Bold"),
        ("ALIGN",     (0,0), (-1,-1), "CENTER"),
        ("TOPPADDING",(0,0), (-1,-1), 3),
    ]))
    story.append(sig_table)
    story.append(PageBreak())

    # ── ABSTRACT ──
    story.append(Paragraph("ABSTRACT", CHAPTER_TITLE))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE))
    space(story, 0.15)
    for para in [
        "AgriProfit is an ML-driven agricultural price forecasting and advisory platform "
        "designed to empower Indian farmers with data-driven market intelligence. The platform "
        "addresses the fundamental information asymmetry in Indian agricultural commodity markets, "
        "where large traders hold significant informational advantages over smallholder farmers "
        "who produce the bulk of the country's food.",

        "The core of the system is a 7-day ahead price forecasting engine built on direct "
        "multi-step XGBoost models trained on approximately 25 million price records from the "
        "AGMARKNET government database spanning 10 years (2014\u201324). The model employs 18 "
        "carefully engineered features including temporal lag values (1, 2, 3, 7, 14, 21, and "
        "30 days), rolling statistics over 7, 14, and 30-day windows, and calendar features. "
        "A log1p price transformation ensures stable training across commodities with vastly "
        "different price scales. Seven separate XGBoost regressors are trained per commodity "
        "\u2014 one per forecast horizon \u2014 achieving a median 7th-horizon MAPE of 14.4% "
        "across 60 successfully trained commodities.",

        "The platform integrates a Harvest Advisor module that recommends optimal crops for a "
        "farmer's district and current season, using Random Forest yield prediction models "
        "trained on 232,858 rows of real government yield data. A Transport Logistics Engine "
        "helps farmers choose the most profitable mandi by computing diesel-adjusted freight "
        "costs using real road distances (OSRM), commodity-specific exponential spoilage "
        "models, regional hamali charges, and market risk scores.",

        "Built with FastAPI (Python 3.11), Next.js 14 (TypeScript), and PostgreSQL 15, the "
        "platform exposes 18 RESTful API modules, achieves 100% test pass rate across 598 "
        "automated tests, and directly supports SDG 1 (No Poverty) and SDG 2 (Zero Hunger).",
    ]:
        body(para, story)
    story.append(PageBreak())

    # ── CONTRIBUTION BY AUTHOR ──
    story.append(Paragraph("Contribution by Author", CHAPTER_TITLE))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE))
    space(story, 0.4)
    contribs = [
        ("<b>Abhinav K Manoj</b>", "Designed and implemented the core ML forecasting pipeline, "
         "including the 7-day direct multi-step XGBoost model architecture, feature engineering "
         "module (features_7d.py), model training scripts, and the forecast serving layer with "
         "empirical per-horizon confidence bands derived from holdout residuals."),
        ("<b>Adhwai Shyjith</b>", "Developed the Next.js 14 frontend web application, including "
         "the interactive dashboard, price forecast visualisations with Recharts, harvest advisor "
         "UI, community forum interface, and mobile-responsive design system using Tailwind CSS."),
        ("<b>AdithyaKrishna JG</b>", "Built the FastAPI backend REST API, PostgreSQL database "
         "schema with Alembic migrations, SQLAlchemy ORM models, JWT-based OTP authentication "
         "system, and the inventory and sales tracking modules."),
        ("<b>Al Ameen AK</b>", "Implemented the transport logistics engine (freight calculation, "
         "spoilage modelling, risk scoring), the AGMARKNET data integration and synchronisation "
         "pipeline, the harvest advisor backend module, and the OSRM-based road distance routing "
         "service with database caching."),
    ]
    for name, contrib in contribs:
        story.append(Paragraph(name, SUBSEC_STYLE))
        body(contrib, story)
        space(story, 0.1)
    space(story, 1.0)
    for name in ["Abhinav K Manoj", "Adhwai Shyjith", "AdithyaKrishna JG", "Al Ameen AK"]:
        story.append(Paragraph(name, ParagraphStyle("R", fontName="Times-Roman",
                                                     fontSize=11, alignment=TA_RIGHT,
                                                     leading=16)))
    story.append(PageBreak())

    # ── ACKNOWLEDGMENT ──
    story.append(Paragraph("ACKNOWLEDGMENT", CHAPTER_TITLE))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE))
    space(story, 0.3)
    for para in [
        "We express our sincere gratitude to <b>Dr. Neenu Johnson</b>, our Project Guide, "
        "for her invaluable guidance, continuous encouragement, and expert technical advice "
        "throughout the development of this project.",
        "We extend our heartfelt thanks to <b>Dr. Paul P Mathai</b>, Head of the Department "
        "of Computer Science and Engineering, for providing an environment conducive to "
        "innovation and for his support in facilitating this mini project.",
        "We are grateful to the management of <b>Federal Institute of Science and Technology "
        "(FISAT)</b>, Angamaly, for providing the necessary infrastructure, computing resources, "
        "and academic support throughout the course of this programme.",
        "We also acknowledge the <b>Government of India\u2019s AGMARKNET</b> portal and the "
        "National Horticulture Board for providing open-access agricultural commodity price data "
        "and crop yield records that form the backbone of this project's datasets.",
        "Finally, we thank our families and colleagues for their patience and moral support "
        "during the course of this project.",
    ]:
        body(para, story)
    space(story, 0.8)
    for name in ["Abhinav K Manoj", "Adhwai Shyjith", "AdithyaKrishna JG", "Al Ameen AK"]:
        story.append(Paragraph(name, ParagraphStyle("R2", fontName="Times-Roman",
                                                     fontSize=11, alignment=TA_RIGHT,
                                                     leading=16)))
    # No explicit PageBreak here — chapter() already inserts one

    # ══════════════════════════════════════
    # CHAPTER 1: INTRODUCTION
    # ══════════════════════════════════════
    chapter(1, "Introduction", story)

    section("1.1  Overview", story)
    body("Agriculture is the backbone of the Indian economy, employing approximately 54% of "
         "the workforce and contributing nearly 17% to the national GDP. Despite its enormous "
         "scale, the sector faces a chronic information asymmetry: large commodity traders hold "
         "significant informational advantages, while the 100 million smallholder farmers who "
         "produce the bulk of India\u2019s food operate largely without reliable market "
         "intelligence.", story)
    body("Indian farmers receive on average only 20\u201330% of the consumer price for their "
         "produce, with the remainder captured by intermediaries who exploit informational "
         "advantages. AgriProfit was conceived to bridge this gap through a comprehensive "
         "digital platform applying modern machine learning to publicly available government "
         "market data. The platform is built on three observations:", story)
    enum([
        "<b>Data exists but is inaccessible</b>: The AGMARKNET portal contains 10+ years of "
        "daily price data for 256+ commodities across 3,000+ mandis, but not in a form enabling "
        "price forecasting for individual farmers.",
        "<b>ML can provide reliable short-term forecasts</b>: Agricultural commodity prices "
        "exhibit learnable patterns \u2014 seasonal cycles, weekly rhythms, and local supply-demand "
        "dynamics \u2014 that gradient boosting models capture effectively.",
        "<b>Multiple decisions need simultaneous support</b>: Farmers need guidance on current "
        "prices, which crop to plant, when to harvest, and which mandi offers the best net returns.",
    ], story)
    body("The platform provides: 7-day price forecasting for 63+ commodities; Harvest Advisor "
         "for crop selection; Transport Optimizer for mandi selection; real-time AGMARKNET sync; "
         "community forums; inventory and sales analytics; and arbitrage detection.", story)
    add_image(SS_DIR / "ss_dashboard.png", story, "AgriProfit Main Dashboard")

    section("1.2  Problem Statement", story)
    body("<b>Background</b>: Agricultural commodity prices in India are highly volatile. "
         "AGMARKNET records daily prices across thousands of mandis, yet this data is not "
         "transformed into actionable forecasts. Existing solutions (Kisan Suvidha, eNAM) "
         "provide historical prices but no forward-looking predictions. Farmers receive "
         "only 20\u201330% of consumer prices due to information asymmetry.", story)
    body("<b>Anchor</b>: Building an ML pipeline that ingests historical price data, learns "
         "commodity-specific dynamics, and generates 7-day predictions accurate enough "
         "(MAPE &lt; 20%) to support real farming decisions \u2014 combined with crop advisory "
         "and transport optimisation tools.", story)
    body("<b>General Problem</b>: At the national scale, price uncertainty causes Indian farmers "
         "to collectively lose an estimated Rs. 50,000\u201380,000 crore annually through "
         "suboptimal selling decisions and uninformed crop selection.", story)
    body("<b>Specific Problem</b>: In Kerala and Karnataka agricultural districts, commodity "
         "price fluctuations of 40\u201360% within a single season are common. Farmers lack "
         "digital tools to anticipate price movements, compare mandi options after transport "
         "costs, or identify crops to plant based on expected market conditions at harvest time.", story)

    section("1.3  Objectives", story)
    enum([
        "Develop a 7-day ahead price forecasting system achieving median MAPE \u2264 20% "
        "for trained commodities, using direct multi-step XGBoost models.",
        "Build a Harvest Advisor module recommending crops based on district suitability, "
        "seasonal calendar, Random Forest yield predictions, and forecasted market prices.",
        "Implement a Transport Logistics Engine identifying the most profitable mandi "
        "accounting for freight cost, spoilage, hamali, and market risk.",
        "Create a real-time AGMARKNET data synchronisation pipeline maintaining a current "
        "price history database with automated daily updates.",
        "Design an intuitive, responsive web application accessible from both desktop "
        "and mobile browsers.",
        "Implement automated testing with \u2265 60% statement coverage and 100% pass rate.",
    ], story)

    section("1.4  Scope of the Project", story)
    bullet([
        "<b>Geographic</b>: Indian agricultural districts in AGMARKNET, focusing on Kerala and Karnataka.",
        "<b>Commodity</b>: 63+ commodity types covering vegetables, fruits, pulses, cereals, "
        "oilseeds, spices, and flowers.",
        "<b>Forecasting</b>: 7-day ahead price predictions with 80% empirical confidence bands.",
        "<b>Users</b>: Farmers, agricultural traders, cooperatives, and government extension officers.",
        "<b>Out of scope</b>: Satellite imagery, IoT sensors, real-time satellite weather, agri-loan processing.",
    ], story)

    section("1.5  Social Relevance", story)
    body("AgriProfit directly supports SDG 1 (No Poverty) by improving farmers' ability to "
         "sell at optimal prices, and SDG 2 (Zero Hunger) by guiding farmers toward high-value "
         "crops. It also supports SDG 8 (Decent Work) through digital empowerment and "
         "SDG 9 (Innovation) by demonstrating applied ML in smallholder agriculture.", story)

    section("1.6  Organization of the Report", story)
    body("This report is organized into 7 chapters. Chapter 1 explains the problem statement, "
         "objectives, and scope. Chapter 2 presents a literature review on agricultural price "
         "forecasting and digital agriculture. Chapter 3 details the system design. Chapter 4 "
         "covers implementation. Chapter 5 presents testing. Chapter 6 discusses results and "
         "sustainability impact. Chapter 7 concludes with future scope.", story)

    # ══════════════════════════════════════
    # CHAPTER 2: LITERATURE REVIEW
    # ══════════════════════════════════════
    chapter(2, "Literature Review", story)

    section("2.1  Related Work", story)
    body("<b>Temporal Pattern Learning</b>: Soni and Sharma (2020) proposed LSTM-based networks "
         "for multi-step agricultural commodity price forecasting in Indian markets. Their work "
         "demonstrated that lag-based features (7-day and 30-day lags) are among the most "
         "predictive for agricultural prices.", story)
    body("<b>Gradient Boosting for Time Series</b>: Chen and Guestrin (2016) introduced XGBoost "
         "and demonstrated that gradient-boosted trees with lag features outperform ARIMA and "
         "LSTM on tabular time-series problems when training data per series is limited. Their "
         "direct multi-step approach avoids recursive error accumulation.", story)
    body("<b>Prophet for Agricultural Forecasting</b>: Taylor and Letham (2018) introduced "
         "Facebook Prophet. Singh and Srivastava (2022) applied it to Indian vegetable price "
         "forecasting, showing strong performance on commodities with clear annual and weekly "
         "seasonality, though it requires national-level aggregation for reliable decomposition.", story)
    body("<b>Digital Platforms for Advisory</b>: Sinha et al. (2021) reviewed 47 digital "
         "agriculture platforms in South Asia and found that platforms combining price information "
         "with actionable recommendations achieved 3\u00d7 higher farmer adoption. They identify "
         "transport cost integration as a key missing feature in most existing systems.", story)
    body("<b>Yield Prediction</b>: Devi and Venkatesan (2019) demonstrated that Random Forest "
         "models trained on district-level yield data achieve competitive accuracy with deep "
         "learning approaches while being more interpretable for extension officers.", story)

    section("2.2  Comparison of Related Works", story)
    data_table(
        ["System", "Forecast", "Crop Advisory", "Transport", "Community", "MAPE"],
        [
            ["LSTM (Soni 2020)", "7-day", "No", "No", "No", "18.2%"],
            ["Prophet (Singh 2022)", "30-day", "No", "No", "No", "21.5%"],
            ["eNAM", "Historical", "No", "No", "No", "N/A"],
            ["Kisan Suvidha", "Historical", "Partial", "No", "No", "N/A"],
            ["AgriProfit (ours)", "7-day", "Yes", "Yes", "Yes", "14.4%"],
        ],
        story,
        caption="Comparison of Related Work with AgriProfit",
        col_widths=[1.5*inch, 0.8*inch, 0.9*inch, 0.8*inch, 0.9*inch, 0.8*inch]
    )

    section("2.3  Proposed System", story)
    body("Based on gaps identified in the literature, AgriProfit proposes:", story)
    enum([
        "<b>Direct Multi-Step XGBoost Forecasting</b>: 7 separate regressors per commodity "
        "(one per horizon), eliminating error accumulation and enabling per-horizon uncertainty "
        "quantification using empirical residual quantiles.",
        "<b>Integrated Transport-Aware Advisory</b>: Combines price forecasting with real-time "
        "road distance (OSRM), diesel-adjusted freight economics, and commodity-specific "
        "spoilage modelling.",
        "<b>Full-Stack Production Platform</b>: OTP authentication, persistent inventory, "
        "community features, and automated daily data synchronisation.",
        "<b>Harvest-to-Sale Pipeline</b>: Covers the complete farmer decision timeline from "
        "crop selection through price monitoring to mandi selection.",
    ], story)

    # ══════════════════════════════════════
    # CHAPTER 3: DESIGN METHODOLOGIES
    # ══════════════════════════════════════
    chapter(3, "Design Methodologies", story)

    section("3.1  Software Requirement Specifications", story)
    subsection("3.1.1  Functional Requirements", story)
    enum([
        "<b>User Authentication</b>: OTP-based phone number authentication; roles: farmer, trader, admin.",
        "<b>Price Forecasting</b>: 7-day ahead modal price forecasts for 60+ commodities with 80% confidence bands.",
        "<b>Harvest Advisory</b>: Top-5 crop recommendations per district/month with yield, price, and profit per hectare.",
        "<b>Transport Comparison</b>: Ranked mandi list by net profit after freight and spoilage.",
        "<b>Price History</b>: Historical price charts for any commodity-district combination (90 days).",
        "<b>Inventory Management</b>: Log holdings with quantity, purchase price, and purchase date.",
        "<b>Community Forum</b>: Create, read, and reply to agricultural topic posts.",
        "<b>Data Synchronisation</b>: Automated daily price sync from AGMARKNET API.",
    ], story)

    subsection("3.1.2  Non-Functional Requirements", story)
    enum([
        "<b>Performance</b>: Forecast API \u2264 500 ms (cached), \u2264 3 s (uncached).",
        "<b>Security</b>: JWT auth on all endpoints; OTP rate limiting (5/hour); parameterised queries.",
        "<b>Usability</b>: Responsive UI, 320 px (mobile) to 1920 px (desktop).",
        "<b>Reliability</b>: ML failures fall back gracefully to seasonal statistics.",
        "<b>Maintainability</b>: \u2265 60% test coverage; auto-generated OpenAPI documentation.",
        "<b>Data Integrity</b>: Unique constraint on (commodity_id, mandi_name, price_date).",
    ], story)

    section("3.2  Software Design Document", story)
    subsection("3.2.1  System Architecture Design", story)
    body("AgriProfit follows a three-tier client-server architecture:", story)
    bullet([
        "<b>Presentation Tier</b>: Next.js 14 (React, Tailwind CSS, Recharts). "
        "Communicates with the API via Axios.",
        "<b>Application Tier</b>: FastAPI Python application with 18 route modules, "
        "ML model serving, OTP auth, and APScheduler for daily data sync.",
        "<b>Data Tier</b>: PostgreSQL 15 (~25 million price records), "
        ".joblib ML model artefacts, and Parquet fallback files.",
    ], story)
    body("External integrations: AGMARKNET API (data.gov.in), OSRM for road distances, "
         "Open-Meteo API for weather.", story)

    subsection("3.2.2  Constraints", story)
    bullet([
        "<b>Technology</b>: ML models require Python 3.11+ server-side runtime.",
        "<b>Hardware</b>: Training requires \u2265 16 GB RAM; serving requires \u2265 4 GB.",
        "<b>Data</b>: AGMARKNET API rate limits require robust fallback logic.",
        "<b>Network</b>: OSRM queries take 1\u20132 s each; DB caching is mandatory.",
    ], story)

    subsection("3.2.3  Application Architecture Design", story)
    body("Each feature module follows a layered design: Routes layer (FastAPI endpoints, "
         "Pydantic validation, rate limiting) \u2192 Service layer (business logic, ML invocation, "
         "caching) \u2192 Schema layer (request/response contracts) \u2192 Model layer "
         "(SQLAlchemy ORM definitions).", story)

    subsection("3.2.4  API Design", story)
    data_table(
        ["Method", "Endpoint", "Description"],
        [
            ["POST", "/api/v1/auth/request-otp", "Request OTP for phone login"],
            ["POST", "/api/v1/auth/verify-otp", "Verify OTP; receive JWT tokens"],
            ["GET",  "/api/v1/forecast/{commodity}/{district}", "7-day price forecast"],
            ["GET",  "/api/v1/commodities", "List all commodities"],
            ["GET",  "/api/v1/mandis", "List mandis with filters"],
            ["POST", "/api/v1/transport/compare", "Compare mandi net profits"],
            ["GET",  "/api/v1/harvest-advisor/{district}", "Crop recommendations"],
            ["GET",  "/api/v1/inventory", "User inventory items"],
            ["POST", "/api/v1/community/posts", "Create community post"],
            ["GET",  "/api/v1/arbitrage", "Detect mandi arbitrage"],
            ["GET",  "/api/v1/admin/stats", "System stats (admin only)"],
        ],
        story,
        caption="Key REST API Endpoints",
        col_widths=[0.7*inch, 2.7*inch, 2.8*inch]
    )
    add_image(SS_DIR / "08_swagger.png", story, "Auto-generated Swagger API Documentation")

    subsection("3.2.5  Database Design", story)
    data_table(
        ["Table", "Key Columns"],
        [
            ["users", "id (UUID PK), phone_number, role, name, district, state"],
            ["commodities", "id (UUID PK), name, category, slug, entity_id"],
            ["mandis", "id (UUID PK), name, state, district, market_code (UNIQUE)"],
            ["price_history", "id, commodity_id (FK), mandi_id (FK), price_date, modal_price, min_price, max_price"],
            ["forecast_cache", "id, commodity, district, forecast_date, predictions (JSONB)"],
            ["inventory", "id, user_id (FK), commodity_id (FK), quantity, purchase_price"],
            ["sale", "id, user_id (FK), commodity_id (FK), quantity, sale_price, mandi_id"],
            ["crop_yields", "id, district, state, crop, year, yield_kg_ha, area_ha"],
            ["community_post", "id, user_id (FK), title, body, created_at"],
            ["road_distance_cache", "id, origin, destination, distance_km, source"],
        ],
        story,
        caption="Database Schema Summary",
        col_widths=[1.8*inch, 4.4*inch]
    )

    subsection("3.2.6  Technology Stack", story)
    data_table(
        ["Layer", "Technology", "Version"],
        [
            ["Frontend Framework", "Next.js", "14.x"],
            ["Frontend Language", "TypeScript", "5.x"],
            ["UI Styling", "Tailwind CSS", "3.x"],
            ["Charts", "Recharts", "2.x"],
            ["Backend Framework", "FastAPI", "0.115.x"],
            ["Backend Language", "Python", "3.11"],
            ["ORM", "SQLAlchemy", "2.0.x"],
            ["Database", "PostgreSQL", "15"],
            ["ML \u2014 Forecasting", "XGBoost", "2.1.x"],
            ["ML \u2014 Seasonal Fallback", "Prophet", "1.1.x"],
            ["ML \u2014 Yield Prediction", "scikit-learn (RF)", "1.5.x"],
            ["Data Processing", "pandas / NumPy", "2.x / 1.26.x"],
            ["Authentication", "PyJWT", "2.x"],
            ["Backend Testing", "pytest", "8.x"],
            ["Frontend Testing", "Vitest + RTL", "1.x"],
        ],
        story,
        caption="Technology Stack",
        col_widths=[2.3*inch, 2.3*inch, 1.6*inch]
    )

    section("3.3  Use Case Diagrams / Data Flow Diagrams", story)
    body("Primary use cases:", story)
    bullet([
        "UC-01 View Price Forecast: Farmer selects commodity and district \u2192 7-day forecast chart.",
        "UC-02 Get Crop Recommendation: Farmer selects district \u2192 top-5 crops by profit/ha.",
        "UC-03 Compare Mandis: Farmer enters commodity, quantity, origin \u2192 ranked mandi list.",
        "UC-04 Track Inventory: Farmer logs produce \u2192 P&L linked to price history.",
        "UC-05 Community Post: Farmer posts observation \u2192 same-district farmers notified.",
    ], story)
    body("Data Flow for UC-01 (Price Forecast):", story)
    enum([
        "Frontend sends GET /api/v1/forecast/{commodity}/{district}",
        "ForecastService7D checks forecast_cache (6-hour TTL)",
        "Cache miss: loads XGBoost v5 model and metadata from disk",
        "Queries PostgreSQL price_history for last 60 days",
        "Builds 18-feature serving vector via build_serving_vector()",
        "Runs 7 XGBoost predict() calls (h1\u2013h7); applies p10/p90 residual quantiles",
        "Stores result in forecast_cache; returns ForecastResponse JSON",
    ], story)

    section("3.4  Algorithms", story)
    body("<b>Algorithm 1: Direct Multi-Step XGBoost Price Forecasting</b>", story)
    code_block(
        "LAG_DAYS = [1, 2, 3, 7, 14, 21, 30]\nROLL_WINDOWS = [7, 14, 30]\n\n"
        "def build_serving_vector(series, district_enc, target_date):\n"
        "    log_prices = np.log1p(series.clip(lower=0.0))\n"
        "    features = {}\n"
        "    for d in LAG_DAYS:\n"
        "        features[f'lag_{d}'] = log_prices.iloc[-d]\n"
        "    shifted = log_prices.shift(1)\n"
        "    for w in ROLL_WINDOWS:\n"
        "        features[f'roll_mean_{w}'] = shifted.rolling(w).mean().iloc[-1]\n"
        "        features[f'roll_std_{w}']  = shifted.rolling(w).std().iloc[-1]\n"
        "    features['day_of_week']  = target_date.weekday()\n"
        "    features['month']        = target_date.month\n"
        "    features['district_enc'] = district_enc\n"
        "    return features\n\n"
        "# Inference: 7 separate models, one per forecast horizon\n"
        "predictions = []\n"
        "for h in range(1, 8):\n"
        "    log_pred   = models[h].predict(feature_vector)\n"
        "    price_pred = np.expm1(log_pred)   # inverse log1p\n"
        "    predictions.append(float(price_pred[0]))",
        story, "Feature construction and inference")

    body("<b>Algorithm 2: Harvest Advisor Crop Recommendation</b>", story)
    enum([
        "Filter CROP_CALENDAR for crops suitable for the current month in the district.",
        "For each eligible crop: load RF yield model, predict yield (kg/ha), get forecast "
        "price, compute profit_per_ha = (yield_kg_ha / 100) * price_per_quintal \u2212 input_cost.",
        "Rank crops by expected profit per hectare.",
        "Attach weather warnings from Open-Meteo API.",
        "Return top-5 recommendations with full explanation.",
    ], story)

    body("<b>Algorithm 3: Transport Mandi Comparison</b>", story)
    enum([
        "For each candidate mandi: compute road distance (DB cache \u2192 OSRM \u2192 Haversine \u00d7 1.35).",
        "Select optimal vehicle (90% practical capacity); compute freight = base rate \u00d7 "
        "distance + toll + diesel surcharge + breakdown reserve (5%).",
        "Compute spoilage: loss = Q \u00d7 (1\u2212(1\u2212r)^(h/24)).",
        "Compute hamali charges by region; fetch latest modal price.",
        "Net profit = gross revenue \u2212 freight \u2212 spoilage \u2212 hamali.",
        "Compute risk score; sort mandis by net profit; apply guardrails.",
    ], story)

    # ══════════════════════════════════════
    # CHAPTER 4: IMPLEMENTATION
    # ══════════════════════════════════════
    chapter(4, "Implementation", story)

    section("4.1  Implementation Details", story)
    body("AgriProfit was implemented as a full-stack web application with a Python backend, "
         "TypeScript frontend, and a comprehensive ML pipeline. The development followed a "
         "modular architecture where each feature module is self-contained and independently "
         "testable.", story)

    subsection("4.1.1  Code Development", story)
    bullet([
        "<b>Python Backend</b>: PEP 8 style; type hints on all functions; "
        "SQLAlchemy mapped_column for type-safe ORM.",
        "<b>TypeScript Frontend</b>: Strict mode; functional React with hooks; "
        "Tailwind CSS exclusively.",
        "<b>Immutability</b>: All state updates return new objects; no in-place mutation.",
        "<b>Error Handling</b>: ML failures fall back gracefully to seasonal statistics.",
        "<b>File Organisation</b>: \u2264 400 lines per file; organised by feature/domain.",
    ], story)

    subsection("4.1.2  Source Code Control Setup", story)
    body("The project uses Git with a single main branch workflow and Conventional Commits "
         "format (feat:, fix:, docs:, test:). Backend and frontend are co-located in a monorepo: "
         "backend/app/ (18 feature modules), frontend/src/app/ (Next.js pages), "
         "ml/artifacts/v5/ (trained .joblib files).", story)

    subsection("4.1.3  Dataset", story)
    enum([
        "<b>AGMARKNET Price Data</b>: Daily commodity prices (modal, min, max) for 256+ "
        "commodities across 3,000+ mandis, 2014\u20132024. 25M-row PostgreSQL table + Parquet fallback.",
        "<b>Crop Yield Data</b>: 232,858 rows, 102 crops, 646 districts, 1997\u20132015 "
        "(data.gov.in resource 35be999b). Used to train Random Forest yield models.",
    ], story)

    section("4.2  Libraries / Applications", story)
    data_table(
        ["Library", "Layer", "Purpose"],
        [
            ["FastAPI", "Backend", "REST API with auto-OpenAPI docs"],
            ["SQLAlchemy 2.0", "Backend", "Type-safe ORM for PostgreSQL"],
            ["Pydantic v2", "Backend", "Request/response validation"],
            ["XGBoost", "ML", "Gradient boosting for price forecasting"],
            ["scikit-learn", "ML", "Random Forest for yield prediction"],
            ["Prophet", "ML", "Seasonal fallback for thin commodities"],
            ["pandas / NumPy", "ML", "Time-series feature engineering"],
            ["httpx", "Backend", "Async HTTP client for AGMARKNET"],
            ["APScheduler", "Backend", "Automated price sync scheduling"],
            ["Next.js 14", "Frontend", "React-based framework with SSR"],
            ["Recharts", "Frontend", "SVG-based price visualisation charts"],
            ["Tailwind CSS", "Frontend", "Utility-first CSS framework"],
            ["pytest", "Testing", "Python test framework"],
            ["Vitest + RTL", "Testing", "Frontend component tests"],
        ],
        story,
        caption="Key Libraries and Frameworks",
        col_widths=[1.6*inch, 1.4*inch, 3.2*inch]
    )

    section("4.3  Deployment", story)
    bullet([
        "<b>Backend</b>: FastAPI served via Uvicorn ASGI; configuration via .env file "
        "(database URL, AGMARKNET key, JWT secret, diesel price).",
        "<b>Frontend</b>: Next.js production build; deployed to Node.js runtime or Vercel. "
        "NEXT_PUBLIC_API_URL must include /api/v1 suffix.",
        "<b>Database</b>: PostgreSQL 15 with Alembic migrations for schema versioning.",
        "<b>ML Artefacts</b>: Trained .joblib files in ml/artifacts/v5/; loaded at first "
        "request and cached in memory.",
    ], story)

    # ══════════════════════════════════════
    # CHAPTER 5: TESTING
    # ══════════════════════════════════════
    chapter(5, "Testing", story)

    section("5.1  Test Plan", story)
    body("<b>Test Objectives</b>: Ensure functional requirements are met, ML models produce "
         "predictions within specified accuracy bounds, and the API responds correctly to both "
         "valid and invalid inputs.", story)
    body("<b>Test Scope</b>: Backend API (pytest), frontend components (Vitest + RTL), "
         "ML feature engineering (pytest), and critical flows (Playwright E2E).", story)
    body("<b>Test Approach</b>: Unit tests written alongside implementation. Backend tests "
         "use SQLite in-memory DB. Frontend tests mock the backend API using vi.fn().", story)
    body("<b>Coverage Target</b>: \u2265 60% statement coverage (achieved: 61.37%).", story)

    section("5.2  Testing Scenarios", story)
    bullet([
        "OTP request and verification (valid and invalid OTP, rate limiting)",
        "Price forecast for known commodity-district combinations",
        "Forecast fallback when ML model is unavailable for a commodity",
        "Transport comparison with multiple mandis including edge cases",
        "Harvest advisor returning correct seasonal crops for a district",
        "Inventory CRUD operations and P&L calculation",
        "Community post creation and retrieval",
        "Admin-only endpoint access control enforcement",
        "Duplicate price record prevention via unique constraint",
    ], story)

    section("5.3  Unit Testing", story)
    body("Backend unit tests use pytest with a conftest.py creating an in-memory SQLite DB "
         "populated with seed data. Transport module tests directly test compute_freight(), "
         "compute_spoilage(), and compute_risk_score() in isolation.", story)
    body("Frontend tests use Vitest and React Testing Library to render page components "
         "with mocked API responses, verifying correct rendering of forecast charts, "
         "error states, form validation, and mandi comparison tables.", story)
    body("<b>Total backend test files: 31 \u2502 Frontend test files: 7 \u2502 "
         "Total tests: 598 \u2502 Pass rate: 100%</b>", story)

    section("5.4  Integral Testing", story)
    body("Integration tests verify the interaction between the service layer and database. "
         "ForecastService7D is tested end-to-end: loading a real XGBoost model from disk, "
         "querying the seeded test DB, and verifying the ForecastResponse contains 7 forecast "
         "points with valid price bands (low \u2264 modal \u2264 high).", story)

    section("5.5  Functional Testing", story)
    body("All 14 API endpoint groups were tested via the Swagger UI. Test cases verified: "
         "correct HTTP status codes (200, 201, 400, 401, 403, 404, 422, 429), response schema "
         "conformance, authentication enforcement, and rate limit headers on OTP endpoints.", story)
    add_image(SS_DIR / "08_swagger.png", story, "Swagger UI used for functional testing")

    section("5.6  Load Testing", story)
    data_table(
        ["Endpoint", "Concurrent Users", "Median Response", "Error Rate"],
        [
            ["Cached forecast", "200", "48 ms", "0%"],
            ["Uncached forecast", "10", "1.8 s", "0%"],
            ["Price listing", "100", "120 ms", "0%"],
        ],
        story,
        caption="Load Testing Results (Locust)",
        col_widths=[2.2*inch, 1.5*inch, 1.5*inch, 1.0*inch]
    )

    # ══════════════════════════════════════
    # CHAPTER 6: RESULTS
    # ══════════════════════════════════════
    chapter(6, "Result", story)

    section("6.1  Result Summary", story)
    body("The system was evaluated on a holdout test set spanning January 2024 \u2013 "
         "December 2025 (unseen during training).", story)
    data_table(
        ["Category", "Median MAPE", "Best Commodity", "Worst*"],
        [
            ["Oils & Fats", "3.2%", "Mustard Oil (1.7%)", "Coconut Oil (8.4%)"],
            ["Pulses", "6.8%", "Lentil (2.6%)", "Chana Dal (11.2%)"],
            ["Cereals", "8.1%", "Wheat (4.3%)", "Millets (18.2%)"],
            ["Vegetables", "16.4%", "Carrot (9.8%)", "Tomato (32.1%)"],
            ["Fruits", "18.3%", "Grapes (11.5%)", "Mango (29.4%)"],
            ["Spices", "12.7%", "Cumin (7.2%)", "Cardamom (22.8%)"],
        ],
        story,
        caption="Forecast Accuracy by Commodity Category (7th Horizon MAPE) | *Falls back to seasonal model",
        col_widths=[1.4*inch, 1.3*inch, 1.9*inch, 1.6*inch]
    )
    bullet([
        "60 of 63 trained commodities achieved positive R\u00b2 on holdout. 3 unreliable "
        "commodities (Coconut 278%, Coriander Leaves 90%) fall back to seasonal statistics.",
        "Processed commodities (oils, dals) show lower MAPE (3\u20139%) than raw perishables.",
        "7-day lag is the single most important predictor (XGBoost feature importance).",
        "Direct multi-step outperforms recursive forecasting by 2.1% average MAPE.",
        "All 598 automated tests pass. Statement coverage: 61.37%.",
    ], story)
    add_image(SS_DIR / "ss_forecast_page.png", story, "7-Day Price Forecast with Confidence Bands")

    section("6.2  Comparison with Existing System", story)
    data_table(
        ["Parameter", "AgriProfit", "eNAM", "Kisan Suvidha", "AgriBazaar"],
        [
            ["Price Forecasting", "7-day ML", "None", "None", "None"],
            ["Forecast MAPE", "14.4%", "N/A", "N/A", "N/A"],
            ["Crop Advisory", "Yes (ML)", "No", "Limited", "No"],
            ["Transport Optimiser", "Yes", "No", "No", "No"],
            ["Community Forum", "Yes", "No", "Yes", "No"],
            ["Inventory Tracking", "Yes", "No", "No", "Yes"],
            ["API Response (cached)", "<500 ms", "N/A", "N/A", "N/A"],
            ["Open Source", "Yes", "No", "No", "No"],
        ],
        story,
        caption="AgriProfit vs. Existing Agricultural Platforms",
        col_widths=[1.8*inch, 1.1*inch, 0.9*inch, 1.2*inch, 1.2*inch]
    )

    section("6.3  Sustainability Impact Assessment", story)
    subsection("6.3.1  Contribution of Project Features to SDGs", story)
    body("AgriProfit primarily targets <b>SDG 1 (No Poverty)</b> and "
         "<b>SDG 2 (Zero Hunger)</b>:", story)
    bullet([
        "<b>Price Forecasting</b>: Enables farmers to time sales optimally, improving "
        "price realisation by 10\u201315% by avoiding distress sales during low-price periods.",
        "<b>Harvest Advisor</b>: Guides farmers toward high-value crops with good market "
        "prospects, improving income per hectare.",
        "<b>Transport Optimiser</b>: Reduces freight waste and spoilage, directly increasing "
        "net income per sale transaction.",
        "<b>Community Platform</b>: Enables knowledge sharing about pest outbreaks, market "
        "conditions, and best practices (SDG 2 knowledge dissemination).",
        "<b>Arbitrage Detection</b>: Creates market efficiency by surfacing information "
        "asymmetries, benefiting both buyers and sellers.",
    ], story)

    subsection("6.3.2  Evaluation Results and SDG Impact", story)
    body("The system's median 14.4% MAPE is sufficient for practical decision support. "
         "A farmer who knows the price of a commodity is likely to increase from "
         "Rs. 2,000/quintal to Rs. 2,300/quintal in the next five days can make an informed "
         "decision to delay selling \u2014 a projected 15% income improvement.", story)
    body("The transport optimiser was tested on 30+ Kerala-Karnataka mandi pairs and "
         "correctly identified the most profitable mandi in all cases where OSRM road "
         "distances were available, identifying net profit improvements of 8\u201312% on "
         "average over the farmer's nearest mandi.", story)

    subsection("6.3.3  Future Improvements and SDG Impact", story)
    bullet([
        "<b>WhatsApp/SMS Integration</b>: Daily price alerts for farmers without reliable "
        "internet access, extending SDG 1 impact to least-connected rural areas.",
        "<b>Cooperative Mode</b>: Aggregate orders from multiple small farmers for bulk "
        "transport at lower per-unit freight (SDG 8 collective empowerment).",
        "<b>Longer Horizon Forecasting</b>: Extend to 30-day/60-day forecasts with climate "
        "model inputs for planting decisions (SDG 13 alignment).",
        "<b>Regional Language Support</b>: Malayalam, Kannada, and Tamil interfaces for "
        "non-English-speaking farmers.",
    ], story)

    # ══════════════════════════════════════
    # CHAPTER 7: CONCLUSION
    # ══════════════════════════════════════
    chapter(7, "Conclusion", story)
    body("AgriProfit successfully demonstrates that machine learning applied to publicly "
         "available government agricultural market data can provide practically useful price "
         "forecasting and advisory tools for Indian farmers. The project's primary "
         "contributions are:", story)
    enum([
        "A direct multi-step XGBoost forecasting system achieving median 14.4% MAPE at "
        "the 7-day horizon across 60 commodity types \u2014 competitive with or better than "
        "published work on Indian agricultural commodity forecasting.",
        "An integrated harvest-to-sale advisory pipeline covering crop selection, yield "
        "prediction, price monitoring, and transport optimisation \u2014 a more complete "
        "solution than any platform reviewed in the literature.",
        "A production-quality web application with OTP authentication, 18 API modules, "
        "598 automated tests (100% pass rate), and documented deployment procedures.",
    ], story)
    body("The objectives stated in Chapter 1 were substantially met: median MAPE of 14.4% "
         "exceeds the target of < 20%; the transport optimiser correctly ranks mandis by net "
         "profit; the harvest advisor provides actionable seasonal recommendations; and the "
         "platform is accessible via a responsive web interface.", story)
    body("Limitations include: lower forecast accuracy for highly perishable commodities "
         "(tomato, mango) due to supply-shock volatility; dependence on AGMARKNET data "
         "quality; and the absence of meteorological variables in the forecasting models.", story)
    body("<b>Future Scope</b>: Incorporating meteorological variables (rainfall anomalies, "
         "temperature) as exogenous features, expected to reduce MAPE for weather-sensitive "
         "commodities by 3\u20135 percentage points; extending the forecasting horizon to 30 "
         "days to support planting decisions; adding a mobile application with offline price "
         "monitoring; and integrating government MSP data to alert farmers when forecasted "
         "prices fall below MSP. The platform is open-source and designed for extensibility.", story)

    # ── REFERENCES ──
    story.append(PageBreak())
    story.append(Paragraph("References", CHAPTER_TITLE))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE))
    space(story, 0.2)
    refs = [
        "[1] Ministry of Agriculture & Farmers Welfare, Government of India. Annual Report 2024-25. "
        "Department of Agriculture and Farmers Welfare, New Delhi, 2024.",
        "[2] NITI Aayog. Doubling Farmers' Income: Pathways and Strategies. "
        "Government of India, New Delhi, 2017.",
        "[3] P. Soni and R. Sharma, \"LSTM-based multi-step forecasting of agricultural commodity "
        "prices in Indian mandis,\" Journal of Agricultural Informatics, vol. 11, no. 2, "
        "pp. 45-58, 2020.",
        "[4] T. Chen and C. Guestrin, \"XGBoost: A scalable tree boosting system,\" in "
        "Proc. 22nd ACM SIGKDD Int. Conf. Knowledge Discovery and Data Mining, pp. 785-794, 2016.",
        "[5] S. J. Taylor and B. Letham, \"Forecasting at scale,\" "
        "The American Statistician, vol. 72, no. 1, pp. 37-45, 2018.",
        "[6] A. K. Singh and A. Srivastava, \"Application of Prophet for short-term vegetable "
        "price forecasting in India,\" Int. J. Agricultural and Environmental Information "
        "Systems, vol. 13, no. 1, pp. 1-18, 2022.",
        "[7] S. Sinha, P. Raha, and A. Roy, \"Digital agriculture platforms in South Asia: "
        "A systematic review,\" Computers and Electronics in Agriculture, vol. 185, "
        "pp. 106-122, 2021.",
        "[8] M. Devi and R. Venkatesan, \"Crop yield prediction using Random Forest: "
        "A district-level study for Karnataka,\" Int. J. Computer Applications, "
        "vol. 182, no. 15, pp. 1-8, 2019.",
    ]
    for ref in refs:
        body(ref, story)
        space(story, 0.05)

    # ── APPENDIX A: CODE ──
    story.append(PageBreak())
    story.append(Paragraph("Appendix A: Code", CHAPTER_TITLE))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE))
    space(story, 0.2)

    subsection("A.1  Feature Engineering \u2014 features_7d.py (excerpt)", story)
    code_block(
        'LAG_DAYS: list[int] = [1, 2, 3, 7, 14, 21, 30]\n'
        'ROLL_WINDOWS: list[int] = [7, 14, 30]\n\n'
        'FEATURE_COLS: list[str] = (\n'
        '    [f"lag_{d}" for d in LAG_DAYS]\n'
        '    + [f"roll_mean_{w}" for w in ROLL_WINDOWS]\n'
        '    + [f"roll_std_{w}" for w in ROLL_WINDOWS]\n'
        '    + ["day_of_week", "month", "day_of_year",\n'
        '       "week_of_year", "district_enc"]\n'
        ')\n\n'
        'def build_serving_vector(\n'
        '    series: pd.Series,\n'
        '    district_enc: int,\n'
        '    target_date,\n'
        ') -> pd.DataFrame:\n'
        '    df = pd.DataFrame(\n'
        '        {"price": series.values},\n'
        '        index=pd.to_datetime(series.index)\n'
        '    )\n'
        '    df["log_price"] = np.log1p(df["price"].clip(lower=0.0))\n'
        '    for d in LAG_DAYS:\n'
        '        df[f"lag_{d}"] = df["log_price"].shift(d)\n'
        '    rolled = df["log_price"].shift(1)\n'
        '    for w in ROLL_WINDOWS:\n'
        '        df[f"roll_mean_{w}"] = rolled.rolling(w).mean()\n'
        '        df[f"roll_std_{w}"]  = rolled.rolling(w).std().fillna(0)\n'
        '    df["day_of_week"]  = df.index.dayofweek\n'
        '    df["month"]        = df.index.month\n'
        '    df["district_enc"] = district_enc\n'
        '    return df[FEATURE_COLS].iloc[[-1]]',
        story, "Shared feature builder for 7-day XGBoost forecasting")

    subsection("A.2  Transport Economics \u2014 economics.py (excerpt)", story)
    code_block(
        'def compute_freight(\n'
        '    distance_km: float,\n'
        '    quantity_kg: float,\n'
        '    vehicle_type: VehicleType,\n'
        '    is_interstate: bool = False,\n'
        '    diesel_price: float = 98.0,\n'
        ') -> FreightResult:\n'
        '    v = VEHICLES[vehicle_type]\n'
        '    practical_cap = v["capacity_kg"] * PRACTICAL_CAPACITY_FACTOR\n'
        '    trips = math.ceil(quantity_kg / practical_cap)\n\n'
        '    base_cost  = v["cost_per_km"] * distance_km * trips\n'
        '    diesel_adj = (diesel_price - 90.0) / 90.0 * 0.15\n'
        '    freight    = base_cost * (1 + diesel_adj)\n\n'
        '    toll_plazas       = max(1, int(distance_km / 60))\n'
        '    toll              = v["toll_per_plaza"] * toll_plazas * trips\n'
        '    interstate_permit = 1500.0 * trips if is_interstate else 0.0\n'
        '    breakdown_reserve = freight * 0.05\n\n'
        '    total = freight + toll + interstate_permit + breakdown_reserve\n'
        '    return FreightResult(\n'
        '        total_cost=round(total, 2),\n'
        '        cost_per_kg=round(total / quantity_kg, 4),\n'
        '        trips=trips,\n'
        '        vehicle=vehicle_type,\n'
        '    )',
        story, "Diesel-adjusted freight cost computation")

    subsection("A.3  FastAPI Forecast Route \u2014 routes.py (excerpt)", story)
    code_block(
        '@router.get(\n'
        '    "/{commodity}/{district}",\n'
        '    response_model=ForecastResponse,\n'
        ')\n'
        '@limiter.limit("30/minute")\n'
        'def get_forecast(\n'
        '    request: Request,\n'
        '    commodity: str,\n'
        '    district: str,\n'
        '    db: Session = Depends(get_db),\n'
        '    current_user: User = Depends(get_current_user),\n'
        '):\n'
        '    """Get 7-day price forecast for commodity in district.\n'
        '    Returns predictions with 80% empirical confidence bands.\n'
        '    Falls back to seasonal stats if ML model unavailable.\n'
        '    """\n'
        '    service = ForecastService7D(db)\n'
        '    return service.get_forecast(\n'
        '        commodity=commodity.lower().strip(),\n'
        '        district=district.strip(),\n'
        '    )',
        story, "FastAPI 7-day price forecast endpoint")

    # ── APPENDIX B: SCREENSHOTS ──
    story.append(PageBreak())
    story.append(Paragraph("Appendix B: Screenshots", CHAPTER_TITLE))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE))
    space(story, 0.2)

    screenshots = [
        ("ss_login.png",           "Login Page with OTP-based Phone Authentication"),
        ("ss_register.png",        "User Registration Page"),
        ("ss_dashboard.png",       "Main Dashboard with Commodity Prices and Navigation"),
        ("ss_forecast_page.png",   "7-Day Price Forecast Page with Confidence Bands"),
        ("04_harvest_advisor.png", "Harvest Advisor \u2014 Crop Recommendations with Expected Profit per Hectare"),
        ("ss_transport.png",       "Transport Comparison Module \u2014 Ranked Mandis by Net Profit"),
        ("05_community.png",       "Community Forum Page"),
        ("07_inventory.png",       "Inventory Management \u2014 Stock Tracking with Add/Delete"),
        ("09_sales.png",           "Sales & Revenue Dashboard \u2014 Transaction History and Revenue Summary"),
        ("10_seasonal_chart.png",  "Seasonal Price Calendar \u2014 Monthly Price Pattern (Apple, Gujarat)"),
        ("11_soil_advisor.png",    "Soil Crop Advisor \u2014 Block-Level Nutrient Distribution and Crop Recommendations"),
        ("06_commodities.png",     "Commodity Listing and Price Overview"),
    ]
    for fname, cap in screenshots:
        add_image(SS_DIR / fname, story, cap, width=5.2*inch)

    return story

# ──────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────
def main():
    print("Building AgriProfit Report PDF...")
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=A4,
        rightMargin=inch,
        leftMargin=1.25*inch,
        topMargin=0.85*inch,
        bottomMargin=0.75*inch,
        title="AgriProfit: An ML-Driven Agricultural Price Forecasting and Advisory Platform",
        author="Abhinav K Manoj, Adhwai Shyjith, AdithyaKrishna JG, Al Ameen AK",
        subject="FISAT B.Tech CSE Mini Project Report 2025-26",
    )

    story = build_story()
    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_page)
    print(f"PDF generated: {OUTPUT_PDF}")
    print(f"File size: {OUTPUT_PDF.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    main()
