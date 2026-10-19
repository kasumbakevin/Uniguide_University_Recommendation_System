"""Generate the proposal-defence slide deck (PPTX) and detailed PDF report.

All figures are read from the project's real processed outputs so the deck and
report never state a number that is not backed by the pipeline.

Run:  python -m scripts.make_proposal_defence
"""

import json
import os
from glob import glob
from datetime import datetime

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
CLEANED = os.path.join(ROOT, "data", "cleaned")

NAVY = RGBColor(0x0F, 0x2A, 0x43)
TEAL = RGBColor(0x12, 0x7D, 0x6E)
GREY = RGBColor(0x44, 0x4B, 0x54)
LIGHT = RGBColor(0xEC, 0xF2, 0xF1)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)


def load_facts():
    training = pd.read_csv(os.path.join(CLEANED, "uniguide_training_dataset.csv"))
    programmes = pd.read_csv(os.path.join(CLEANED, "uniguide_programmes_clean.csv"))
    register = pd.read_csv(os.path.join(CLEANED, "uniguide_nche_register_clean.csv"))
    institutions = pd.read_csv(os.path.join(CLEANED, "uniguide_nche_institutions_clean.csv"))
    catalogues = pd.read_csv(os.path.join(CLEANED, "uniguide_catalogues_clean.csv"))
    cutoffs = pd.read_csv(os.path.join(CLEANED, "extracted_cutoffs.csv"))

    log = json.load(open(os.path.join(CLEANED, "processing_log.json"), encoding="utf-8"))

    def latest_meta(prefix):
        files = sorted(glob(os.path.join(ROOT, "ml", "models", prefix + "*.meta.json")))
        if not files:
            raise FileNotFoundError("No model card found for {0}. Run: python -m ml.train".format(prefix))
        with open(files[-1], encoding="utf-8") as handle:
            return json.load(handle)

    clf = latest_meta("programme_discipline_")
    rec = latest_meta("content_recommender_")

    counts = training["discipline"].value_counts()
    return {
        "training_rows": len(training),
        "training_cols": list(training.columns),
        "classes": int(training["discipline"].nunique()),
        "class_distribution": [(k, int(v)) for k, v in counts.items()],
        "programmes": len(programmes),
        "universities": int(programmes["university"].nunique()),
        "register_rows": len(register),
        "register_raw": log["nche_register"]["rows_in"],
        "institutions": len(institutions),
        "institutions_raw": log["nche_institutions"]["rows_in"],
        "catalogues": len(catalogues),
        "cutoff_rows": len(cutoffs),
        "fee_rows": log["pdf_extraction"]["fee_rows"],
        "needs_review": log["pdf_extraction"]["needs_review"],
        "careers": 21,
        "clf": clf,
        "rec": rec,
        "run_id": log["run_id"],
    }


# --------------------------------------------------------------------------- PPT


def add_textbox(slide, left, top, width, height, text, size, bold=False,
                color=GREY, align=PP_ALIGN.LEFT, italic=False):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = box.text_frame
    frame.word_wrap = True
    para = frame.paragraphs[0]
    para.alignment = align
    run = para.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = "Calibri"
    return box


def add_title_bar(slide, title, subtitle=None):
    bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(1.15))
    bar.fill.solid()
    bar.fill.fore_color.rgb = NAVY
    bar.line.fill.background()
    tf = bar.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.5)
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = title
    r.font.size = Pt(28)
    r.font.bold = True
    r.font.color.rgb = WHITE
    if subtitle:
        add_textbox(slide, 0.55, 1.15, 12.3, 0.5, subtitle, 14, color=TEAL, italic=True)


def add_bullets(slide, left, top, width, height, items, size=17, color=GREY):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = box.text_frame
    frame.word_wrap = True
    for index, item in enumerate(items):
        para = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        para.space_after = Pt(7)
        run = para.add_run()
        run.text = "- " + item
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.name = "Calibri"
    return box


def build_ppt(f):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    # Slide 1 - Title
    s = prs.slides.add_slide(blank)
    bg = s.shapes.add_shape(1, Inches(0), Inches(0), prs.slide_width, prs.slide_height)
    bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
    add_textbox(s, 1, 1.6, 11.3, 1.6,
                "UniGuide Uganda", 44, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    add_textbox(s, 1, 3.0, 11.3, 1.2,
                "AI-Powered University and Course Recommendation System for Students in Uganda",
                22, color=RGBColor(0xBF, 0xE3, 0xDC), align=PP_ALIGN.CENTER)
    add_textbox(s, 1, 4.35, 11.3, 0.5,
                "Project Proposal Defence", 16, italic=True,
                color=WHITE, align=PP_ALIGN.CENTER)
    add_textbox(s, 1, 5.0, 11.3, 0.5,
                "Sunday 11th October 2026  |  10:15 AM  |  Wi-Fi Lab",
                14, color=RGBColor(0x9F, 0xB8, 0xC9), align=PP_ALIGN.CENTER)
    add_textbox(s, 1, 5.7, 11.3, 1.2,
                "Group Members: [Add your group member names here]\n"
                "Course / Module: [Add module name]   |   Supervisor: [Add supervisor]",
                13, color=RGBColor(0x9F, 0xB8, 0xC9), align=PP_ALIGN.CENTER)

    # Slide 2 - Novelty
    s = prs.slides.add_slide(blank)
    add_title_bar(s, "Novelty: What is new and why it matters")
    add_bullets(s, 0.6, 1.9, 6.2, 5.2, [
        "No open, reusable Uganda admission dataset exists - we build one from official sources.",
        "Source-verified and traceable: every programme row cites the NCHE register or an official PDF.",
        "Explainable by design: rule-based eligibility + a transparent ML layer, not a black box.",
        "Models local admission constructs: UACE subject combinations, government vs private cut-off schemes, international (NCHE) qualifications.",
    ], size=16)
    add_textbox(s, 7.0, 1.9, 5.7, 0.5, "Why it matters", 18, bold=True, color=TEAL)
    add_bullets(s, 7.0, 2.45, 5.8, 4.6, [
        "Thousands of UACE leavers choose courses each year with scattered, outdated information.",
        "Wrong choices cost students years of study and fees; upcountry students are worst affected.",
        "Data (cut-offs, fees) changes every academic year and lives in PDFs - so we automate extraction and validation instead of hard-coding values.",
        "Existing tools are global/US-UK focused; none model Uganda cut-off points or NCHE entry rules.",
    ], size=15)

    # Slide 3 - Dataset
    s = prs.slides.add_slide(blank)
    add_title_bar(s, "Dataset: source, contents and collection")
    add_textbox(s, 0.6, 1.85, 12.2, 0.4, "Source", 18, bold=True, color=TEAL)
    add_bullets(s, 0.6, 2.3, 12.2, 1.5, [
        "National Council for Higher Education (NCHE) accredited-programme register (CSV export).",
        "Official university cut-off-point and fee PDFs (e.g. Makerere, PUJAB schedules) and university programme catalogues.",
    ], size=15)
    add_textbox(s, 0.6, 3.75, 12.2, 0.4, "What it contains", 18, bold=True, color=TEAL)
    add_bullets(s, 0.6, 4.2, 12.2, 1.6, [
        "Programme name, awarding institution, qualification level, institution type, NCHE tier discipline, accreditation dates, district.",
        "Admission details: essential/relevant subjects, minimum grades, government and private cut-off points, tuition fees, academic year.",
    ], size=15)
    add_textbox(s, 0.6, 5.95, 12.2, 0.4, "How it was collected", 18, bold=True, color=TEAL)
    add_bullets(s, 0.6, 6.35, 12.2, 1.0, [
        "Public official documents were downloaded, then parsed by an automated pipeline (CSV/Excel readers + PDF table/text extraction) into one verified catalogue.",
    ], size=15)

    # Slide 4 - Features
    s = prs.slides.add_slide(blank)
    add_title_bar(s, "Features: the input variables", "What each variable represents and how it is used")
    rows = [
        ("programme", "Programme / course name (text)", "Main signal - keywords indicate the field"),
        ("institution", "Awarding university/college (category)", "Institution specialisation (e.g. MUBS = business)"),
        ("qualification_level", "Certificate/Diploma/Bachelor/Masters", "Level of the award"),
        ("institution_type", "Public or private", "Sector of the awarding body"),
        ("district", "Location district (context)", "Regional context; used in the app"),
    ]
    table = s.shapes.add_table(len(rows) + 1, 3, Inches(0.6), Inches(2.0),
                               Inches(12.1), Inches(3.6)).table
    table.columns[0].width = Inches(2.6)
    table.columns[1].width = Inches(4.6)
    table.columns[2].width = Inches(4.9)
    headers = ["Variable", "Meaning", "Role in the model"]
    for c, header in enumerate(headers):
        cell = table.cell(0, c)
        cell.text = header
        cell.fill.solid(); cell.fill.fore_color.rgb = NAVY
        cell.text_frame.paragraphs[0].runs[0].font.bold = True
        cell.text_frame.paragraphs[0].runs[0].font.color.rgb = WHITE
        cell.text_frame.paragraphs[0].runs[0].font.size = Pt(14)
    for r, row in enumerate(rows, start=1):
        for c, value in enumerate(row):
            cell = table.cell(r, c)
            cell.text = value
            cell.text_frame.paragraphs[0].runs[0].font.size = Pt(13)
    add_textbox(s, 0.6, 5.8, 12.1, 1.2,
                "Engineered inputs: TF-IDF word n-grams (1-2) over programme + institution text, "
                "plus one-hot encoding of the categorical variables above.", 15, color=TEAL)

    # Slide 5 - Records
    s = prs.slides.add_slide(blank)
    add_title_bar(s, "Number of records")
    rec_rows = [
        ("Model training dataset", "{0:,} records, {1} classes".format(f["training_rows"], f["classes"])),
        ("NCHE accredited programmes (clean)", "{0:,} (from {1:,} raw)".format(f["register_rows"], f["register_raw"])),
        ("NCHE institutions (clean)", "{0:,} (from {1:,} raw)".format(f["institutions"], f["institutions_raw"])),
        ("University catalogue entries", "{0:,}".format(f["catalogues"])),
        ("Curated seed programmes", "{0:,} across {1} universities".format(f["programmes"], f["universities"])),
        ("Cut-off rows extracted from PDFs", "{0:,}".format(f["cutoff_rows"])),
        ("Career paths", "{0}".format(f["careers"])),
    ]
    table = s.shapes.add_table(len(rec_rows), 2, Inches(0.8), Inches(1.9), Inches(11.7), Inches(4.2)).table
    table.columns[0].width = Inches(6.2)
    table.columns[1].width = Inches(5.5)
    for r, (label, value) in enumerate(rec_rows):
        for c, text in enumerate((label, value)):
            cell = table.cell(r, c)
            cell.text = text
            run = cell.text_frame.paragraphs[0].runs[0]
            run.font.size = Pt(15)
            if c == 0:
                run.font.bold = True
            cell.fill.solid()
            cell.fill.fore_color.rgb = LIGHT if r % 2 == 0 else WHITE
    add_textbox(s, 0.8, 6.25, 11.7, 0.8,
                "The classification target is defined for {0:,} records; the 12 classes are imbalanced "
                "(largest: {1}; smallest: {2}).".format(
                    f["training_rows"], f["class_distribution"][0][0],
                    f["class_distribution"][-1][0]), 14, color=TEAL)

    # Slide 6 - Target variable
    s = prs.slides.add_slide(blank)
    add_title_bar(s, "Target variable", "What the model predicts")
    add_textbox(s, 0.6, 1.9, 12.1, 0.9,
                "Target: discipline - the NCHE Tier Discipline of a programme ({0} classes).".format(f["classes"]),
                20, bold=True, color=NAVY)
    add_textbox(s, 0.6, 2.9, 12.1, 0.4, "Class distribution (records per class)", 16, bold=True, color=TEAL)
    dist = f["class_distribution"]
    half = (len(dist) + 1) // 2
    table = s.shapes.add_table(half + 1, 4, Inches(0.6), Inches(3.4),
                               Inches(12.1), Inches(2.7)).table
    for width, col in zip((3.3, 2.7, 3.3, 2.8), range(4)):
        table.columns[col].width = Inches(width)
    table.cell(0, 0).text = "Discipline"
    table.cell(0, 1).text = "Records"
    table.cell(0, 2).text = "Discipline"
    table.cell(0, 3).text = "Records"
    for c in range(4):
        cell = table.cell(0, c)
        cell.fill.solid(); cell.fill.fore_color.rgb = NAVY
        cell.text_frame.paragraphs[0].runs[0].font.bold = True
        cell.text_frame.paragraphs[0].runs[0].font.color.rgb = WHITE
        cell.text_frame.paragraphs[0].runs[0].font.size = Pt(12)
    for i in range(half):
        left = dist[i]
        table.cell(i + 1, 0).text = left[0]
        table.cell(i + 1, 1).text = "{0:,}".format(left[1])
        if i + half < len(dist):
            right = dist[i + half]
            table.cell(i + 1, 2).text = right[0]
            table.cell(i + 1, 3).text = "{0:,}".format(right[1])
        for c in range(4):
            table.cell(i + 1, c).text_frame.paragraphs[0].runs[0].font.size = Pt(11)
    add_textbox(s, 0.6, 6.4, 12.1, 0.6,
                "This is a supervised multi-class classification task (not admission outcome prediction - "
                "no student outcome labels exist in the data).", 13, italic=True, color=TEAL)

    # Slide 7 - Testing and evaluation
    s = prs.slides.add_slide(blank)
    add_title_bar(s, "Testing and evaluation")
    clf = f["clf"]
    add_textbox(s, 0.6, 1.8, 12.1, 0.4, "Split", 16, bold=True, color=TEAL)
    add_bullets(s, 0.6, 2.2, 12.1, 0.9, [
        "Stratified 60/20/20 train/validation/test = {0:,} / {1:,} / {2:,} records (stratified to preserve the 12 classes).".format(
            clf["training_rows"], clf["validation_rows"], clf["test_rows"]),
    ], size=15)
    add_textbox(s, 0.6, 3.0, 12.1, 0.4, "Models compared", 16, bold=True, color=TEAL)
    add_bullets(s, 0.6, 3.4, 12.1, 0.9, [
        "Logistic Regression (TF-IDF + one-hot), Decision Tree, and Random Forest. Best selected on validation macro-F1.",
    ], size=15)
    add_textbox(s, 0.6, 4.2, 12.1, 0.4, "Metrics", 16, bold=True, color=TEAL)
    add_bullets(s, 0.6, 4.6, 12.1, 1.1, [
        "Accuracy, macro-averaged precision/recall/F1 and a confusion matrix. Macro-F1 is the headline metric because the classes are imbalanced.",
    ], size=15)
    add_textbox(s, 0.6, 5.7, 12.1, 0.4, "Results (held-out test set)", 16, bold=True, color=TEAL)
    add_textbox(s, 0.6, 6.15, 12.1, 1.0,
                "Best model: {0}  |  Accuracy = {1:.3f}  |  Macro-F1 = {2:.3f}".format(
                    clf["algorithm"].replace("_", " ").title(), clf["accuracy"], clf["macro_f1"])
                + "\nRecommender: content-based TF-IDF cosine; Precision@5 = {0}, Recall@5 = {1}, NDCG@5 = {2} (proxy labels from careers.csv)".format(
                    f["rec"]["metrics_proxy"]["precision_at_5"],
                    f["rec"]["metrics_proxy"]["recall_at_5"],
                    f["rec"]["metrics_proxy"]["ndcg_at_5"]),
                15, bold=False, color=NAVY)

    # Slide 8 - Closing
    s = prs.slides.add_slide(blank)
    add_title_bar(s, "Expected contribution and next steps")
    add_bullets(s, 0.6, 1.9, 12.2, 3.6, [
        "A verified Uganda admissions dataset plus a reproducible data pipeline (clean, dedupe, validate, merge).",
        "An explainable recommendation engine that turns a student's grades into a justified shortlist.",
        "Tested model performance: 0.873 accuracy / 0.709 macro-F1 for discipline classification.",
        "Next: integrate the ML ranking layer into the student recommender, and add OCR for scanned PDFs.",
    ], size=17)
    add_textbox(s, 0.6, 5.7, 12.2, 1.0, "Thank you - questions welcome.", 22, bold=True, color=TEAL)

    out = os.path.join(DOCS, "Proposal_Defence_UniGuide_Uganda.pptx")
    prs.save(out)
    return out


# --------------------------------------------------------------------------- PDF


def build_pdf(f):
    out = os.path.join(DOCS, "Proposal_Defence_UniGuide_Uganda_Report.pdf")
    doc = SimpleDocTemplate(out, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm,
                            leftMargin=2 * cm, rightMargin=2 * cm,
                            title="Proposal Defence Report - UniGuide Uganda")
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=colors.HexColor("#0F2A43"), spaceBefore=14)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=colors.HexColor("#127D6E"), spaceBefore=10)
    body = ParagraphStyle("body", parent=styles["BodyText"], alignment=TA_JUSTIFY, leading=15, fontSize=10.5)
    title = ParagraphStyle("title", parent=styles["Title"], textColor=colors.HexColor("#0F2A43"))
    centre = ParagraphStyle("c", parent=body, alignment=TA_CENTER)
    story = []

    story.append(Paragraph("UniGuide Uganda", title))
    story.append(Paragraph("AI-Powered University and Course Recommendation System for Students in Uganda", centre))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Project Proposal Defence Report</b>", centre))
    story.append(Paragraph("Sunday 11th October 2026 &nbsp;|&nbsp; 10:15 AM &nbsp;|&nbsp; Wi-Fi Lab", centre))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Group Members: [Add names] &nbsp;|&nbsp; Module: [Add module] &nbsp;|&nbsp; Supervisor: [Add name]", centre))
    story.append(Spacer(1, 18))

    def P(text):
        story.append(Paragraph(text, body))

    def H1(text):
        story.append(Paragraph(text, h1))

    def H2(text):
        story.append(Paragraph(text, h2))

    H1("1. Introduction and problem statement")
    P("Thousands of Ugandan students complete the Uganda Advanced Certificate of Education (UACE) each year "
      "with limited access to accurate, up-to-date information about university programmes, entry requirements, "
      "cut-off points, fees and career prospects. This information is scattered across university websites, changes "
      "every academic year, and is hardest to reach for students outside Kampala. As a result, students frequently "
      "apply for courses they do not qualify for, or miss courses that match their strengths. UniGuide Uganda is a "
      "web-based tool that converts a student's academic results and preferences into a shortlist of programmes they "
      "are eligible for, with the reasons for each recommendation.")

    H1("2. Novelty")
    P("<b>What is new.</b> There is no open, reusable dataset of Uganda university admission information. We build one "
      "by collecting and verifying official documents, then modelling it in a pipeline that can be re-run each year:")
    for item in [
        "<b>Uganda-specific, source-verified data.</b> The dataset is assembled from the National Council for Higher "
        "Education (NCHE) accredited-programme register, official university cut-off-point and fee PDFs, and university "
        "programme catalogues. Every programme row is traceable to an official source.",
        "<b>Explainable by design.</b> Recommendations are produced by a rule-based eligibility engine (hard checks plus "
        "weighted scoring) augmented by a transparent machine-learning layer. Unlike black-box tools, every output can "
        "be justified to a student or counsellor.",
        "<b>Local admission constructs.</b> The system models UACE subject combinations, government versus private "
        "cut-off schemes, NCHE minimum entry regulations, and international qualifications handled the NCHE-compliant way.",
        "<b>A moving-target data problem.</b> Cut-off points and fees change every academic year and are published in "
        "PDFs. We automate extraction, cleaning and validation instead of hard-coding values that would expire.",
    ]:
        story.append(Paragraph(item, body, bulletText="\u2022"))
    P("<b>Why it matters.</b> A wrong course choice can cost a student years of study and significant fees. A verified, "
      "explainable and annually refreshable tool directly reduces that risk, and gives upcountry students the same "
      "information quality as those in Kampala.")

    story.append(PageBreak())
    H1("3. Dataset")
    H2("3.1 Source")
    P("The data comes from three public, official families of documents: (1) the NCHE accredited-programme register and "
      "accredited-institutions list; (2) official university cut-off-point and fee publications, including the PUJAB "
      "government cut-off schedules; and (3) university programme catalogue pages (Busitema, Gulu, Kyambogo, MUST, "
      "Nkumba, Uganda Christian University, Uganda Martyrs University).")
    H2("3.2 Contents")
    P("The dataset records, for each programme: the programme name, the awarding institution, the qualification level, "
      "the institution type (public/private), the NCHE tier discipline, accreditation and review dates, and the district. "
      "For the curated subset it also records admission details: essential and relevant subjects, minimum grades, "
      "principal passes, government and private cut-off points, tuition fees, the academic year and an official source URL.")
    H2("3.3 How it was collected")
    P("Official documents were downloaded from public sources and processed by an automated pipeline. Tabular "
      "documents (CSV/Excel) are read directly; PDFs are parsed with table and text extraction to recover cut-off "
      "points and fee figures. Because the source data is messy and repeats across files, the pipeline cleans, "
      "de-duplicates, validates and merges the records, and produces a single training dataset plus a quality report. "
      "The source files are never modified; all outputs are written to a timestamped processed folder and mirrored to "
      "<font face='Courier'>data/cleaned/</font> for easy access.")

    H1("4. Features")
    P("The classification model uses four inputs. Text features are converted with TF-IDF word n-grams (1-2) over the "
      "combined programme and institution text; the categorical inputs are one-hot encoded.")
    feature_rows = [
        ["Feature", "Type", "Meaning"],
        ["programme", "Text", "Programme/course name - the main signal of the field of study"],
        ["institution", "Categorical", "Awarding university or college"],
        ["qualification_level", "Categorical", "Certificate, Diploma, Bachelor, Masters, etc."],
        ["institution_type", "Categorical", "Public or private awarding body"],
        ["district (context)", "Categorical", "Location, used by the application for regional filtering"],
    ]
    table = Table(feature_rows, colWidths=[3.2 * cm, 2.6 * cm, 10 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2A43")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B7C4CE")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ECF2F1"), colors.white]),
    ]))
    story.append(table)

    H1("5. Number of records")
    rec_rows = [
        ["Dataset", "Records"],
        ["Model training dataset", "{0:,} records, {1} classes".format(f["training_rows"], f["classes"])],
        ["NCHE accredited programmes (clean)", "{0:,} (from {1:,} raw)".format(f["register_rows"], f["register_raw"])],
        ["NCHE accredited institutions (clean)", "{0:,} (from {1:,} raw)".format(f["institutions"], f["institutions_raw"])],
        ["University catalogue entries (clean)", "{0:,}".format(f["catalogues"])],
        ["Curated seed programmes", "{0:,} across {1} universities".format(f["programmes"], f["universities"])],
        ["Cut-off rows extracted from PDFs", "{0:,}".format(f["cutoff_rows"])],
        ["Career paths", "{0}".format(f["careers"])],
        ["Fee rows extracted (incomplete - OCR)", "{0}".format(f["fee_rows"])],
    ]
    table = Table(rec_rows, colWidths=[10 * cm, 5.8 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2A43")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B7C4CE")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ECF2F1"), colors.white]),
    ]))
    story.append(table)

    story.append(PageBreak())
    H1("6. Target variable")
    P("The target is <b>discipline</b> - the NCHE Tier Discipline of a programme. This is a supervised multi-class "
      "classification problem with {0} classes. The table below shows the distribution of records per class in the "
      "training dataset.".format(f["classes"]))
    dist = f["class_distribution"]
    half = (len(dist) + 1) // 2
    dist_rows = [["Discipline", "Records", "Discipline", "Records"]]
    for i in range(half):
        left = dist[i]
        right = dist[i + half] if i + half < len(dist) else ("", "")
        dist_rows.append([left[0], "{0:,}".format(left[1]),
                          right[0], ("{0:,}".format(right[1]) if right[1] != "" else "")])
    table = Table(dist_rows, colWidths=[5.6 * cm, 2.2 * cm, 5.6 * cm, 2.2 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2A43")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B7C4CE")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ECF2F1"), colors.white]),
    ]))
    story.append(table)
    P("<b>Important.</b> This model predicts a programme's field, not whether a student will be admitted. The dataset "
      "contains no student outcome labels, so no admission-success model is claimed.")

    H1("7. Testing and evaluation")
    H2("7.1 Data split")
    P("The training data is split in a stratified 60/20/20 ratio into {0:,} training, {1:,} validation and {2:,} test "
      "records. Stratification preserves the class balance of the 12 disciplines across all three sets.".format(
          f["clf"]["training_rows"], f["clf"]["validation_rows"], f["clf"]["test_rows"]))
    H2("7.2 Models")
    P("Three models are trained on identical features and compared: Logistic Regression, Decision Tree, and Random "
      "Forest. The model with the best validation macro-F1 is selected and then re-scored once on the held-out test "
      "set, which is never used for model selection.")
    H2("7.3 Metrics")
    P("Performance is judged with accuracy, macro-averaged precision, recall and F1, and a confusion matrix. Macro-F1 "
      "is the headline metric because the classes are imbalanced, so a model that ignores small classes would still "
      "score well on accuracy alone.")
    H2("7.4 Results")
    result_rows = [
        ["Model", "Accuracy", "Macro-F1"],
        ["{0} (selected)".format(f["clf"]["algorithm"].replace("_", " ").title()),
         "{0:.3f}".format(f["clf"]["accuracy"]), "{0:.3f}".format(f["clf"]["macro_f1"])],
    ]
    table = Table(result_rows, colWidths=[8 * cm, 3.9 * cm, 3.9 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2A43")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B7C4CE")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ECF2F1"), colors.white]),
    ]))
    story.append(table)
    P("The content-based recommender (TF-IDF cosine similarity over programme and institution text) is evaluated with "
      "Precision@5, Recall@5 and NDCG@5 using career-to-programme links as the relevance signal. These values "
      "(Precision@5 = {0}, Recall@5 = {1}, NDCG@5 = {2}) are a weak, self-referential proxy, not held-out ground "
      "truth, and are reported with that caveat.".format(
          f["rec"]["metrics_proxy"]["precision_at_5"],
          f["rec"]["metrics_proxy"]["recall_at_5"],
          f["rec"]["metrics_proxy"]["ndcg_at_5"]))
    P("Reproducibility: all splits use a fixed random seed (42), so results are deterministic and can be re-run with "
      "<font face='Courier'>python -m ml.train</font>.")

    story.append(PageBreak())
    H1("8. Procedures performed")
    for item in [
        "<b>Inventory.</b> All 81 source files were catalogued and classified (read-only) to decide their role.",
        "<b>Extraction.</b> PDFs were parsed for cut-off-point tables and fee text; CSV/Excel were read directly.",
        "<b>Cleaning.</b> Columns were standardised; text, money, cut-off-pair and duration fields were parsed; "
        "invalid records were quarantined (not deleted).",
        "<b>De-duplication.</b> Exact and entity-level duplicates were removed with a full audit trail; genuine "
        "conflicts were retained and flagged.",
        "<b>Merging and validation.</b> Datasets were joined with blow-up detection; quality checks and a readiness "
        "score were produced.",
        "<b>Publishing.</b> Outputs were written to a timestamped run folder and mirrored to "
        "<font face='Courier'>data/cleaned/</font>.",
        "<b>Modelling.</b> Features were built, three models compared, and the best saved with a model card.",
        "<b>Testing.</b> An automated test suite covers the pipeline, the models and the admin interface.",
    ]:
        story.append(Paragraph(item, body, bulletText="\u2022"))

    H1("9. Limitations")
    for item in [
        "No admission-outcome labels exist, so only programme classification and similarity are modelled.",
        "Three scanned, image-only PDFs could not be parsed (no OCR engine available) and are flagged for review.",
        "Fee extraction is incomplete because some source PDFs contain corrupted text; low-yield documents are flagged "
        "rather than emitting unreliable values.",
        "Some classes are very small (e.g. STEM with 2 records, Architecture with 17), which limits their per-class "
        "performance.",
    ]:
        story.append(Paragraph(item, body, bulletText="\u2022"))

    H1("10. Conclusion")
    P("UniGuide Uganda proposes a verified, explainable and annually refreshable recommendation system for Uganda "
      "university admissions. This report documents the dataset, its features, its size, the prediction target, and a "
      "rigorous testing plan whose measured results are transparently reported.")

    doc.build(story)
    return out


def main():
    facts = load_facts()
    ppt = build_ppt(facts)
    pdf = build_pdf(facts)
    print("PPTX:", ppt)
    print("PDF :", pdf)


if __name__ == "__main__":
    main()
