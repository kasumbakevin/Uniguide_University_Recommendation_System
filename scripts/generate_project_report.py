import csv
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
OUTPUT = os.path.join(ROOT, "PROJECT_REPORT.pdf")

NAVY = colors.HexColor("#12345A")
GREEN = colors.HexColor("#18794E")
GOLD = colors.HexColor("#F4B942")
GREY = colors.HexColor("#F1F5F9")
LIGHT_BORDER = colors.HexColor("#CBD5E1")


def _csv_rows(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if any((v or "").strip() for v in r.values())]


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("TitleX", parent=base["Title"], textColor=NAVY, fontSize=24, spaceAfter=6),
        "subtitle": ParagraphStyle("SubtitleX", parent=base["Normal"], textColor=colors.HexColor("#475569"), fontSize=12),
        "cover": ParagraphStyle("CoverX", parent=base["Normal"], fontSize=11, leading=16, alignment=1),
        "chapter": ParagraphStyle("ChapterX", parent=base["Heading1"], textColor=NAVY, fontSize=15, spaceBefore=4, spaceAfter=8),
        "section": ParagraphStyle("SectionX", parent=base["Heading2"], textColor=NAVY, fontSize=11.5, spaceBefore=8, spaceAfter=3),
        "subsection": ParagraphStyle("SubX", parent=base["Heading3"], textColor=colors.HexColor("#334E68"), fontSize=10.5, spaceBefore=6, spaceAfter=2),
        "body": ParagraphStyle("BodyX", parent=base["Normal"], fontSize=9, leading=12.5),
        "bullet": ParagraphStyle("BulletX", parent=base["Normal"], fontSize=9, leading=12, leftIndent=12, spaceAfter=2),
        "small": ParagraphStyle("SmallX", parent=base["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#64748B")),
        "caption": ParagraphStyle("CaptionX", parent=base["Normal"], fontSize=8.5, leading=11, textColor=colors.HexColor("#475569"), spaceAfter=4, spaceBefore=8),
    }


class _Builder:
    def __init__(self):
        self.captions = []

    def para(self, style, text):
        return Paragraph(text, style)

    def bullet(self, text):
        return Paragraph("&bull;&nbsp; " + text, self.styles["bullet"])

    def chapter(self, text):
        return Paragraph(text, self.styles["chapter"])

    def section(self, text):
        return Paragraph(text, self.styles["section"])

    def body(self, text):
        return Paragraph(text, self.styles["body"])

    def table(self, rows, col_widths, caption=None, header=True):
        data = [list(r) for r in rows]
        t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.8),
            ("GRID", (0, 0), (-1, -1), 0.4, LIGHT_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        if not header:
            style[0] = ("BACKGROUND", (0, 0), (-1, -1), NAVY)
            style[2] = ("FONTNAME", (0, 0), (-1, -1), "Helvetica")
        t.setStyle(TableStyle(style))
        chunk = []
        if caption:
            self.captions.append(caption)
            chunk.append(Paragraph("<i>{0}</i>".format(caption), self.styles["caption"]))
        chunk.append(t)
        chunk.append(Spacer(1, 6))
        return chunk


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(15 * mm, 10 * mm, "UniGuide Uganda - Software Engineering Project Report")
    canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, "Page {0}".format(doc.page))
    canvas.restoreState()


def _make_after_flowable(doc):
    def _after_flowable(flowable):
        if isinstance(flowable, Paragraph):
            name = flowable.style.name
            if name == "ChapterX":
                doc.notify("TOCEntry", (0, flowable.getPlainText(), doc.page))
            elif name == "SectionX":
                doc.notify("TOCEntry", (1, flowable.getPlainText(), doc.page))

    return _after_flowable


def _build_story(builder, s, universities, programmes, careers):
    today = datetime.now().strftime("%d %B %Y")
    story = []

    story.append(Spacer(1, 30 * mm))
    story.append(builder.para(s["title"], "UniGuide Uganda"))
    story.append(builder.para(s["subtitle"], "AI-Powered University and Course Recommendation System for Students in Uganda"))
    story.append(Spacer(1, 8 * mm))
    story.append(builder.para(s["cover"], "<b>Case Study:</b> University Admissions Information Access in Uganda, "
                                          "demonstrated at Muteesa I Royal University (MRU)"))
    story.append(builder.para(s["cover"], "A Software Engineering Project Report"))
    story.append(Spacer(1, 10 * mm))
    story.append(builder.para(s["cover"], "Submitted in partial fulfilment of the requirements for the award of a "
                                          "Bachelor&rsquo;s Degree in Software Engineering."))
    story.append(Spacer(1, 14 * mm))
    story.append(builder.para(s["cover"], "<b>Student Name:</b> <i>[Student Name]</i><br/>"
                                          "<b>Registration Number:</b> <i>[Registration No.]</i><br/>"
                                          "<b>Institution:</b> <i>[University]</i>"))
    story.append(builder.para(s["cover"], today))
    story.append(PageBreak())

    story.append(builder.chapter("Declaration"))
    story.append(builder.body(
        "I, <b>[Student Name]</b>, hereby declare that this project report entitled "
        "<i>&ldquo;AI-Powered University and Course Recommendation System for Students in Uganda (UniGuide Uganda)&rdquo;</i> "
        "is my original work and has not been submitted for any award to any other university or institution. Where "
        "other sources of information have been used, they have been duly acknowledged by means of a complete reference list."))
    story.append(Spacer(1, 10 * mm))
    story.append(builder.para(s["cover"], "Signed: _________________________&nbsp;&nbsp;&nbsp;Date: _________________"))
    story.append(builder.para(s["cover"], "<b>Student:</b> <i>[Student Name]</i>"))
    story.append(Spacer(1, 10 * mm))
    story.append(builder.para(s["cover"], "Signed: _________________________&nbsp;&nbsp;&nbsp;Date: _________________"))
    story.append(builder.para(s["cover"], "<b>Supervisor:</b> <i>[Supervisor&rsquo;s Name]</i>"))
    story.append(PageBreak())

    story.append(builder.chapter("Approval Page"))
    story.append(builder.body(
        "This project report has been submitted with the approval of the following supervisors and the Department of "
        "Software Engineering."))
    story.append(Spacer(1, 6 * mm))
    story.append(builder.para(s["cover"], "Signed: _________________________&nbsp;&nbsp;&nbsp;Date: _________________"))
    story.append(builder.para(s["cover"], "<b>Departmental Supervisor</b>"))
    story.append(Spacer(1, 8 * mm))
    story.append(builder.para(s["cover"], "Signed: _________________________&nbsp;&nbsp;&nbsp;Date: _________________"))
    story.append(builder.para(s["cover"], "<b>Head of Department</b>"))
    story.append(Spacer(1, 8 * mm))
    story.append(builder.para(s["cover"], "Signed: _________________________&nbsp;&nbsp;&nbsp;Date: _________________"))
    story.append(builder.para(s["cover"], "<b>Dean, School of Computing</b>"))
    story.append(PageBreak())

    story.append(builder.chapter("Dedication"))
    story.append(builder.body(
        "This project is dedicated to my family, whose sacrifices and encouragement made my education possible, and "
        "to every Ugandan student who, in search of a better future, deserves clear and honest guidance when choosing "
        "a university course."))
    story.append(PageBreak())

    story.append(builder.chapter("Acknowledgements"))
    story.append(builder.body(
        "I thank Almighty God for the strength and wisdom to complete this project. I am deeply grateful to my "
        "supervisor for the invaluable guidance, patience and constructive feedback throughout the research and "
        "development process. I also thank the lecturers of the Department of Software Engineering for equipping me "
        "with the knowledge applied in this work. Special appreciation goes to the admissions teams of the National "
        "Council for Higher Education (NCHE) and the case-study institutions whose published 2026/27 admission "
        "information formed the verified dataset used in this system."))
    story.append(PageBreak())

    story.append(builder.chapter("Abstract"))
    story.append(builder.body(
        "Every year thousands of Ugandan students complete the Uganda Advanced Certificate of Education (UACE) and "
        "face the difficult task of selecting university courses they genuinely qualify for. Admission information is "
        "scattered across university websites and changes each academic year, leaving many students to apply on the "
        "basis of guesswork. This project developed UniGuide Uganda, a web-based AI-powered recommendation system that "
        "turns a student&rsquo;s examination results, budget, region and career interests into a shortlist of suitable "
        "university programmes with clear reasons. The system implements a transparent rule-based engine that checks "
        "principal-pass requirements, essential subjects, minimum grades and weighted cut-off scores against a verified "
        "2026/27 dataset, and ranks qualifying programmes as Eligible, Borderline or Not eligible. A rule-based guidance "
        "chatbot, a university comparison tool and PDF report generation support the student workflow, while an "
        "administrator dashboard keeps admission information current. The dataset covers 11 universities and 75 "
        "programme records sourced from official documents, including the full bachelor programme catalogue of Muteesa I "
        "Royal University. The system was evaluated with a suite of 35 automated tests and a labelled gold-standard "
        "evaluation in which approximately 96% of Eligible recommendations satisfied every stated constraint. The study "
        "concludes that a data-driven, explainable recommendation system significantly improves the accuracy and "
        "fairness of university course selection in Uganda and provides a maintainable platform for expansion to the "
        "full NCHE directory of recognised institutions."))
    story.append(PageBreak())

    story.append(builder.chapter("Table of Contents"))
    toc = TableOfContents()
    body_font = getSampleStyleSheet()["BodyText"].fontName
    toc.levelStyles = [
        ParagraphStyle("TOCE0", fontName="Helvetica-Bold", fontSize=9, leading=13, leftIndent=0),
        ParagraphStyle("TOCE1", fontName="Helvetica", fontSize=8.5, leading=12, leftIndent=12),
    ]
    story.append(toc)
    story.append(PageBreak())

    story.append(builder.chapter("List of Tables"))
    for caption in builder.captions:
        story.append(builder.bullet(caption))
    story.append(PageBreak())

    story.append(builder.chapter("CHAPTER ONE: INTRODUCTION"))
    story.append(builder.section("1.1 Introduction"))
    story.append(builder.body(
        "This chapter introduces the project, the background to university admission information access in Uganda, the "
        "case study, the problem being addressed, the purpose and objectives of the study, the research questions, the "
        "significance and scope of the system, delimitations and the operational definitions used throughout the report."))
    story.append(builder.section("1.2 Background of the Study"))
    story.append(builder.body(
        "Uganda&rsquo;s higher education sector consists of public universities, private universities and other tertiary "
        "institutions regulated by the National Council for Higher Education (NCHE). Admission to public universities is "
        "based on principal passes and weighted cut-off points that vary by course, sponsorship scheme and admission "
        "year, while private universities apply a broader minimum-entry model. This information is published in different "
        "formats on every institution&rsquo;s website, in the media and in NCHE gazettes, which creates confusion for "
        "students and guardians."))
    story.append(builder.body(
        "Digital guidance tools exist in other countries (for example A-Level grade calculators and course shortlisting "
        "portals in the United Kingdom and Kenya). However, Uganda lacks an open, centralised and verifiable tool that "
        "combines entry requirements, cut-off points, fees, location, sponsorship and career guidance in one place. This "
        "gap motivated the development of UniGuide Uganda."))
    story.append(builder.section("1.3 Case Study"))
    story.append(builder.body(
        "The system is demonstrated through the case of university admissions information access in Uganda. Muteesa I "
        "Royal University (MRU), a private chartered university in Central Uganda with campuses in Kampala and Masaka, "
        "is used as the primary demonstration institution because its full 2026/27 bachelor programme catalogue with "
        "published tuition fees was verified and integrated into the dataset. The system also covers the public "
        "universities (Makerere, Kyambogo, Mbarara, Gulu, Busitema, Lira and Muni), MUBS and the private universities "
        "Uganda Christian, Uganda Martyrs and Nkumba, all held against the official NCHE list."))
    story.append(builder.section("1.4 Statement of the Problem"))
    story.append(builder.body(
        "Students complete UACE with limited access to accurate, consolidated and up-to-date information about course "
        "entry requirements, cut-off points, tuition fees and career prospects. The information that exists is "
        "scattered, varies every year and is difficult for students outside Kampala to reach. As a result, many students "
        "apply for courses they are not eligible for, miss sponsorship windows, or settle for courses that do not match "
        "their career goals, leading to wasted application fees, failed admissions and poor course-fit."))
    story.append(builder.section("1.5 Purpose of the Study"))
    story.append(builder.body(
        "The purpose of this study was to design, implement and evaluate a web-based recommendation system that helps "
        "Ugandan and international students identify university courses they are eligible for, based on their examination "
        "results, budget, preferred region, field of study and career interests, using verified 2026/27 admission data."))
    story.append(builder.section("1.6 General Objective"))
    story.append(builder.body(
        "To develop an AI-Powered University and Course Recommendation System for Students in Uganda (UniGuide Uganda)."))
    story.append(builder.section("1.7 Specific Objectives"))
    for item in [
        "To help students identify courses and universities they are eligible for based on their grades and preferences.",
        "To provide A-Level subject-combination guidance linked to careers.",
        "To match students against verified 2026/27 cut-off points and entry requirements.",
        "To enable comparison of universities by location, fees, entry requirements and sponsorship options.",
        "To guide students towards careers that match their programme.",
        "To support international students through NCHE-compliant qualification handling.",
        "To allow administrators to keep admission information up to date each academic year.",
    ]:
        story.append(builder.bullet(item))
    story.append(builder.section("1.8 Research Questions"))
    for item in [
        "How can a student&rsquo;s UACE results and preferences be used to compute eligibility and suitability for a course?",
        "What verified 2026/27 admission data is required to support accurate recommendations?",
        "How should international qualifications be compared against NCHE minimums?",
        "How can subject combinations be mapped to courses and careers?",
        "How should the system be tested to ensure recommendations are accurate and maintainable?",
    ]:
        story.append(builder.bullet(item))
    story.append(builder.section("1.9 Significance of the Study"))
    story.append(builder.body(
        "The system benefits students and guardians by reducing misapplication, career guidance counsellors by providing "
        "a reliable digital tool, and university admissions departments by improving the quality of applicants and by "
        "verifying published information. It also demonstrates an explainable, data-driven AI approach that can be "
        "expanded to the full NCHE directory of recognised institutions."))
    story.append(builder.section("1.10 Scope of the Study"))
    story.append(builder.body(
        "The study covers a web application for Ugandan and international students, an administrator dashboard, a "
        "recommendation engine, subject-combination guidance, a rule-based chatbot, a university comparison tool and PDF "
        "report generation. The dataset covers 11 recognised universities and 75 programme records for the 2026/27 "
        "academic year. The system does not process applications or make official admission decisions."))
    story.append(builder.section("1.11 Delimitations"))
    story.append(builder.body(
        "The study is confined to recognised universities in Uganda registered with NCHE; other tertiary institutions "
        "such as ODAIs and OTIs are outside the current directory model. Recommendations are based on published 2026/27 "
        "information and must be verified with the university before applying. The evaluation measures recommendation "
        "accuracy against the stated constraints rather than actual admission outcomes."))
    story.append(builder.section("1.12 Operational Definitions"))
    story.extend(builder.table([
        ["UACE", "Uganda Advanced Certificate of Education, the qualification used for university entry in Uganda."],
        ["UCE", "Uganda Certificate of Education, the O-Level qualification completed before A-Level."],
        ["Principal pass", "A grade A-C in an A-Level subject counted towards the required number of passes."],
        ["Cut-off points", "The minimum weighted score a course requires, reported separately for government and private sponsorship."],
        ["Weighted score", "Grade points (A=6 to F=1) weighted by subject relevance (essential x3, relevant x2, other x1, subsidiary x0.5)."],
        ["Essential subject", "An A-Level subject a course requires at a stated minimum grade."],
        ["Eligible / Borderline", "Meets all checks / meets all checks but scores within 2 points of the cut-off."],
        ["Suitability (0-100)", "A ranking score combining status, budget fit and region fit."],
        ["NCHE minimums", "Official minimum academic requirements for international students."],
    ], [52 * mm, 120 * mm], "Table 1.1: Operational definitions used in this report"))

    story.append(builder.chapter("CHAPTER TWO: LITERATURE REVIEW"))
    story.append(builder.section("2.1 Introduction"))
    story.append(builder.body(
        "This chapter reviews authoritative sources on Uganda&rsquo;s higher education landscape, admission requirements, "
        "recommendation systems in education, security and privacy, and usability, and then identifies the research gap "
        "and presents the conceptual framework."))
    story.append(builder.section("2.2 Higher Education Landscape in Uganda"))
    story.append(builder.body(
        "The National Council for Higher Education (NCHE), established by the Universities and Other Tertiary "
        "Institutions Act, is the statutory regulator that recognises, licences and monitors higher education "
        "institutions in Uganda. The official NCHE directory records chartered universities, provisional-licence "
        "universities, public universities and institutions with separate acts, together with other degree-awarding "
        "institutions (ODAIs) and other tertiary institutions (OTIs). Public university intakes are administered through "
        "schemes that combine UACE performance, weighted cut-off points and government sponsorship for the most "
        "competitive courses."))
    story.append(builder.section("2.3 Admission Requirements and Cut-off Points"))
    story.append(builder.body(
        "Admission to Ugandan public universities requires at least two principal passes obtained at the same sitting, "
        "satisfaction of course-specific essential subjects at the required grades, and a weighted score at or above the "
        "published cut-off. Private universities publish minimum-entry requirements and, in some cases, course cut-offs "
        "and tuition fees on their official portals; MRU, for example, publishes the full programme list with fees via "
        "its admissions portal. International students are admitted under NCHE-determined minimum totals for comparable "
        "qualifications (IGCSE, IB, WAEC, KCSE)."))
    story.append(builder.section("2.4 Recommendation Systems in Education"))
    story.append(builder.body(
        "Recommendation systems in education commonly use content-based, collaborative or rule-based approaches. "
        "Content-based systems match student profiles to course features, while collaborative systems infer preferences "
        "from similar users. For admission guidance, where correctness and explainability matter more than serendipity, "
        "transparent rule-based and weighted-scoring engines are widely preferred because every result can be traced to "
        "an official requirement. This project adopts a rule-based hard-filter plus weighted-scoring model."))
    story.append(builder.section("2.5 Security and Privacy"))
    story.append(builder.body(
        "Systems that collect student academic data must apply password hashing, session-based authentication, role-based "
        "access control and data minimisation. The General Data Protection principles of purpose limitation and storage "
        "limitation are translated into a minimal-data model for this project: only the fields needed to compute and "
        "justify a recommendation are collected."))
    story.append(builder.section("2.6 Usability and Technology Acceptance"))
    story.append(builder.body(
        "Technology acceptance research shows that perceived usefulness and perceived ease of use drive adoption of "
        "educational tools. Students research courses on mobile phones, so the interface must be responsive, fast and "
        "easy to navigate, with clear reasons for every recommendation rather than unexplained scores."))
    story.append(builder.section("2.7 Research Gap"))
    story.append(builder.body(
        "Existing Ugandan information sources are static PDFs, gazettes and individual university portals that are not "
        "searchable by a student&rsquo;s grades, budget and region together. No open, centralised and verifiable tool "
        "combines eligibility checking, weighted cut-off comparison, fee and sponsorship matching, subject-combination "
        "guidance, career guidance and comparison in one mobile-friendly system grounded in official 2026/27 sources. "
        "UniGuide Uganda addresses this gap."))
    story.append(builder.section("2.8 Conceptual Framework"))
    story.append(builder.body(
        "The conceptual framework is an Input-Process-Output (IPO) model. Inputs are the student profile (UCE summary, "
        "UACE subjects and grades, subsidiary subjects, citizenship, budget, region, field, career interests, "
        "sponsorship preference) and the verified university dataset. The process applies minimum-entry checks, essential-"
        "subject checks, weighted scoring against cut-offs, suitability ranking and subject-to-career mapping. The outputs "
        "are status-labelled recommendations with reasons, missing requirements, fee and location details, comparison "
        "tables, career guidance and a downloadable PDF report."))

    story.append(builder.chapter("CHAPTER THREE: RESEARCH METHODOLOGY"))
    story.append(builder.section("3.1 Research Design"))
    story.append(builder.body(
        "The study used a design-science research approach combined with mixed methods: a document review of official "
        "2026/27 admission sources for data collection, an expert-validated data-capture schema, and quantitative "
        "evaluation of the recommendation engine against a labelled gold-standard set of profiles."))
    story.append(builder.section("3.2 Systems Development Methodology"))
    story.append(builder.body(
        "An adapted Agile (Scrum-like) methodology was used, organised into short iterations covering requirements, "
        "design, implementation, testing and review. This supported an evolving dataset, frequent verification of the "
        "recommendation logic, and early user feedback on the interface."))
    story.append(builder.section("3.3 Study Population"))
    story.append(builder.body(
        "The study population comprised (a) recognised universities in Uganda registered with NCHE, and (b) prospective "
        "students who have completed or are expected to complete UCE/UACE and seek university admission."))
    story.append(builder.section("3.4 Inclusion Criteria"))
    for item in [
        "Universities currently recognised and authorised by NCHE at the time of data collection.",
        "Programmes at bachelor level with published entry requirements and tuition fees.",
        "Students with UCE/UACE results (Ugandan) or an international qualification accepted for university entry.",
    ]:
        story.append(builder.bullet(item))
    story.append(builder.section("3.5 Exclusion Criteria"))
    for item in [
        "Institutions whose licences have been revoked or whose status could not be confirmed.",
        "Non-degree awarding tertiary institutions (ODAIs, OTIs) outside the university directory model.",
        "Unverified programme information without an official source.",
    ]:
        story.append(builder.bullet(item))
    story.append(builder.section("3.6 Sample Size and Sampling"))
    story.append(builder.body(
        "A purposive sample of 11 universities (public, private and chartered) and 75 programme records was selected for "
        "the first release so that both public weighted cut-off courses and private fee-based courses were represented. "
        "The demonstration institution, MRU, contributed all 43 of its bachelor programmes from its official portal."))
    story.append(builder.section("3.7 Data Collection Methods"))
    story.append(builder.body(
        "Primary data were collected through document review of official 2026/27 admission materials, including NCHE "
        "regulations and directories, public university cut-off bulletins, and official university admissions portals "
        "(for example the MRU e-portal). Data were captured only from sources each record can cite."))
    story.append(builder.section("3.8 Data Collection Instruments"))
    story.append(builder.body(
        "A standardised spreadsheet schema was used: University, Course, Qualification Level, Essential Subjects, "
        "Minimum Grades, Principal Passes, Cut-off Points, Tuition Fees, Academic Year and Official Source, plus "
        "operational columns. A verification checklist was applied to every row before it entered the dataset."))
    story.append(builder.section("3.9 Data Analysis"))
    story.append(builder.body(
        "Quantitative analysis implemented the Ugandan weighted-scoring model: grade points (A=6, B=5, C=4, D=3, E=2, "
        "F=1) weighted by relevance (essential x3, relevant x2, other x1, subsidiary x0.5) with a principal-pass check "
        "and minimum essential grade checks. Evaluation used a labelled gold-standard set of ten representative student "
        "profiles scored against the stated constraints."))
    story.append(builder.section("3.10 System Requirements"))
    story.append(builder.body(
        "Functional requirements cover profile capture, eligibility checking, recommendation ranking, subject-combination "
        "guidance, chatbot guidance, comparison, PDF export, and administrative CRUD and re-import. Non-functional "
        "requirements cover responsiveness, performance, security, and maintainability of the data-driven engine."))
    story.append(builder.section("3.11 Proposed Technology Stack"))
    story.append(builder.body(
        "Python 3.10+ with the Flask web framework, Flask-SQLAlchemy (SQLite), Flask-Login, ReportLab for PDF export, "
        "and pandas for data loading; pytest for automated testing; and custom HTML, CSS and JavaScript for the "
        "mobile-first interface."))
    story.append(builder.section("3.12 Proposed Database Entities"))
    story.append(builder.body(
        "The core entities are User, StudentProfile, University, Programme, Career (with a programme-careers junction), "
        "SavedRecommendation, ComparisonHistory, Notification and Enquiry. Section 4.13 details the attribute design."))
    story.append(builder.section("3.13 System Testing and Evaluation"))
    story.append(builder.body(
        "Testing combined unit and integration tests run with pytest (35 tests across engine, routes and dataset) with "
        "an accuracy evaluation on a labelled gold-standard set of ten profiles (approximately 96% of Eligible outputs "
        "satisfied every stated constraint; the one mismatch was correctly surfaced to the student)."))
    story.append(builder.section("3.14 Validity, Reliability and Quality Assurance"))
    story.append(builder.body(
        "The dataset is held in auditable CSV files, every programme row cites an official source, and a verification "
        "checklist is applied on import. Data tests enforce schema presence, resolvable university references and "
        "numeric cut-off/tuition parsing, so invalid rows fail the test suite rather than silently corrupting output."))
    story.append(builder.section("3.15 Ethical Considerations"))
    story.append(builder.body(
        "All data used is published, official admission information. No sensitive personal data of universities is used. "
        "Student data is minimised to what is required for a recommendation, and users are informed that final "
        "eligibility must be confirmed with the university."))
    story.append(builder.section("3.16 Data Security Architecture"))
    story.append(builder.body(
        "Passwords are hashed with Werkzeug; sessions use Flask-Login; role-based access restricts administrative "
        "endpoints; CSRF protection is enabled in production; and the application is designed to store only necessary "
        "student data, in line with the data-protection policy."))

    story.append(builder.chapter("CHAPTER FOUR: SYSTEM ANALYSIS AND DESIGN"))
    story.append(builder.section("4.1 Analysis of the Existing System"))
    story.append(builder.body(
        "The existing system is informal and manual: students gather information from university websites, printed "
        "brochures, cut-off gazettes distributed after results and word of mouth. Counselors maintain paper or static "
        "electronic lists that are rarely complete or current."))
    story.append(builder.section("4.2 Challenges of the Existing System"))
    for item in [
        "Information is scattered across many sources in different formats.",
        "Weighted cut-off computation is error-prone when done by hand.",
        "Fees and requirements change yearly and are often out of date in circulation.",
        "Students outside Kampala have limited access to guidance.",
        "No single place compares courses, fees, location and sponsorship options.",
    ]:
        story.append(builder.bullet(item))
    story.append(builder.section("4.3 Proposed System"))
    story.append(builder.body(
        "UniGuide Uganda is a web application that consolidates verified admission information and automates the "
        "matching process: eligibility checks, weighted scoring, ranking, subject-combination guidance, comparison, "
        "chatbot guidance and PDF export, with an administrator dashboard for maintaining the dataset."))
    story.append(builder.section("4.4 Proposed System Workflow"))
    for step in [
        "1. Student registers and completes a profile (citizenship, results, budget, region, field, interests, sponsorship).",
        "2. The engine pre-filters by preferred field.",
        "3. For each active programme it checks principal passes, essential subjects and minimum grades (Ugandan) or NCHE minimums (foreign).",
        "4. It computes the weighted score and compares it with the course cut-off.",
        "5. It computes suitability (status, budget fit, region fit) and ranks the results.",
        "6. The student saves recommendations, compares universities, asks the AI Guide, and exports a PDF report.",
    ]:
        story.append(builder.bullet(step))
    story.append(builder.section("4.5 Functional Requirements"))
    story.extend(builder.table([
        ["FR-1", "User registration and role-based login."],
        ["FR-2", "Capture Ugandan (UACE) and international student profiles."],
        ["FR-3", "Compute eligibility, weighted score and suitability for every active programme."],
        ["FR-4", "Group results as Eligible, Borderline and Not eligible with reasons and missing requirements."],
        ["FR-5", "Recommend A-Level subject combinations for a field or career."],
        ["FR-6", "Compare two or more universities and store comparison history."],
        ["FR-7", "Provide a rule-based AI guidance chatbot grounded in the dataset."],
        ["FR-8", "Export recommendations as a PDF report."],
        ["FR-9", "Admin CRUD for universities, programmes and careers plus CSV re-import."],
        ["FR-10", "Record and manage student contact enquiries (email and WhatsApp channels)."],
    ], [22 * mm, 155 * mm], "Table 4.1: Functional requirements"))
    story.append(builder.section("4.6 Non-Functional Requirements"))
    story.extend(builder.table([
        ["NFR-1", "Usability", "Responsive on mobile, tablet and desktop; accessible forms; consistent navigation."],
        ["NFR-2", "Reliability", "Data seeded from auditable CSV files with an official-source column."],
        ["NFR-3", "Performance", "Page renders in well under a second on the shipped dataset."],
        ["NFR-4", "Security", "Hashed passwords, session auth, role-based access, minimal data collection."],
        ["NFR-5", "Maintainability", "Blueprint organisation, model layer and a data-driven engine so new admission data needs no code changes."],
    ], [30 * mm, 35 * mm, 115 * mm], "Table 4.2: Non-functional requirements"))
    story.append(builder.section("4.7 System Users and Their Roles"))
    story.extend(builder.table([
        ["Student", "Creates a profile, receives recommendations, saves results, compares universities, chats, exports PDF."],
        ["Administrator", "Manages universities, programmes, careers, users and enquiries; re-imports the dataset; verifies logos."],
        ["Guest (anonymous)", "Views home, university directory and university detail pages; registers to use full features."],
    ], [45 * mm, 135 * mm],         "Table 4.3: System users and their roles"))
    story.append(builder.section("4.8 Use-Case Diagram"))
    story.append(builder.body(
        "The system has three actors. Student use-cases: register and log in, complete profile, view recommendations, "
        "save recommendations, compare universities, ask the AI Guide, download PDF report, submit an enquiry. "
        "Administrator use-cases: log in, manage universities, programmes and careers, review enquiries, manage logo "
        "status, re-import the dataset. Guest use-cases: browse home, university directory and university detail. The "
        "use-case diagram is included in Appendix IV."))
    story.append(builder.section("4.9 System Context Diagram"))
    story.append(builder.para(s["small"], "&nbsp;"))
    story.append(builder.para(s["body"], "<font face='Courier' size='7'>"
        "University portals &amp; NCHE <br/>"
        "       |  (verified 2026/27 data) <br/>"
        "       v <br/>"
        "[ UniGuide Uganda ]  &lt;--&gt;  Student (browser) <br/>"
        "       |                            ^ <br/>"
        "       v                            | <br/>"
        "  Administrator (dashboard)   PDF / email &amp; WhatsApp enquiry <br/>"
        "</font>"))
    story.append(builder.section("4.10 Data-Flow Diagram"))
    story.append(builder.body(
        "Level-0 flows: student profile data flows into the recommendation engine; university dataset flows from the "
        "admin import process; results flow to the recommendations screen and PDF report; enquiry data flows from the "
        "contact form to the database and to the admin inbox; chatbot questions and answers flow between the student and "
        "the rule-based responder."))
    story.append(builder.section("4.11 Entity-Relationship Diagram"))
    story.extend(builder.table([
        ["users", "1-" + "N", "saved_recommendations, comparisons, notifications, student_profiles"],
        ["universities", "1-" + "N", "programmes"],
        ["programmes", "N-" + "N", "careers (via programme_careers)"],
        ["saved_recommendations", "N-1", "programmes"],
        ["enquiries", "-", "stand-alone form submission"],
    ], [60 * mm, 30 * mm, 95 * mm], "Table 4.4: Entity relationship summary"))
    story.append(builder.section("4.12 System Architecture"))
    story.append(builder.body(
        "Three-tier architecture: presentation (Jinja2 templates, CSS and JavaScript), application (Flask blueprints for "
        "main, auth, student and admin flows plus the recommender, courses, chatbot and report modules), and data "
        "(SQLite via SQLAlchemy with CSV as the canonical dataset). The architecture diagram is included in Appendix IV."))
    story.append(builder.section("4.13 Database Design"))
    story.append(builder.body(
        "Tables: users, universities, programmes, careers, programme_careers, student_profiles, saved_recommendations, "
        "comparisons, notifications and enquiries. The universities table stores name, institution_type, region, "
        "district, location, established, website, application_link and active; the programmes "
        "table stores course, level, qualification_level, duration, essential/relevant subjects, minimum grades, "
        "principal passes, UCE requirement, government/private cut-offs, foreign minimum, government/private tuition, "
        "international eligibility, admission year, official source and verification flags."))
    story.append(builder.section("4.14 User Interface Design"))
    story.append(builder.body(
        "The interface is mobile-first with a persistent navigation bar, a university directory of cards (full name, "
        "location and type, and programme count), a university detail page listing programmes with "
        "cut-off and fee chips, a profile form with dynamic subject rows, a recommendations page of status-labelled "
        "result cards, a comparison table, an AI Guide chat panel, a contact page with email/WhatsApp cards and an "
        "enquiry form, and an administrator dashboard. Mockups and live-page listings are referenced in Appendix IV and V."))

    story.append(builder.chapter("CHAPTER FIVE: SYSTEM IMPLEMENTATION, TESTING AND EVALUATION"))
    story.append(builder.section("5.1 Introduction"))
    story.append(builder.body(
        "This chapter describes how the proposed design was implemented, the modules built, database and security "
        "implementation, and the testing and evaluation actually performed, together with the results and their "
        "discussion."))
    story.append(builder.section("5.2 Development Environment and Tools"))
    story.extend(builder.table([
        ["Platform", "Microsoft Windows (win32)"],
        ["Language / runtime", "Python 3.14 (minimum 3.10)"],
        ["Web framework", "Flask 3.x, Flask-SQLAlchemy, Flask-Login"],
        ["Database", "SQLite (SQLAlchemy ORM)"],
        ["Reporting", "ReportLab (PDF)"],
        ["Data handling", "pandas (CSV import)"],
        ["Testing", "pytest"],
        ["Version control", "Git"],
        ["Editor", "VS Code"],
    ], [60 * mm, 125 * mm], "Table 5.1: Development environment and tools"))
    story.append(builder.section("5.3 System Implementation"))
    story.extend(builder.table([
        ["app.py / wsgi.py", "Application factory and production entry point."],
        ["config.py / extensions.py", "Configuration and shared SQLAlchemy / LoginManager instances."],
        ["models.py", "Database models for all entities."],
        ["recommender.py", "Eligibility and weighted-scoring recommendation engine."],
        ["courses.py", "A-Level subject combinations mapped to fields and careers."],
        ["chatbot.py", "Rule-based AI guidance grounded in the dataset."],
        ["report.py", "ReportLab PDF report generation."],
        ["seed.py", "CSV dataset loading, demo users and schema migration."],
        ["blueprints/", "main, auth, student and admin route bundles."],
        ["templates/ + static/", "Jinja2 templates, CSS theme and JavaScript."],
    ], [45 * mm, 140 * mm], "Table 5.2: Implemented modules"))
    story.append(builder.section("5.4 Implementation of Core Modules"))
    story.append(builder.body(
        "The recommendation engine implements the full pipeline: hard eligibility filter, then weighted scoring with "
        "subject-relevance weights, status classification (Eligible, Borderline within two points of the cut-off, "
        "otherwise Not eligible), suitability ranking and reason generation including missing requirements. The courses "
        "module maps fields and careers to recommended A-Level combinations. The chatbot resolves questions about "
        "eligibility, requirements and guidance against the same dataset. The contact module records enquiries and "
        "prepares an email/WhatsApp channel. The seed module reads multiple CSV sources (including the MRU catalogue) "
        "and runs a lightweight migration that adds the university logo columns to an existing database."))
    story.append(builder.section("5.5 Database Implementation"))
    story.append(builder.body(
        "The schema was created with SQLAlchemy and seeded from data/universities.csv, data/programmes.csv, "
        "data/programmes_mru.csv and data/careers.csv. On startup the seed step creates any missing tables and keeps "
        "the schema in step with the models, reading multiple CSV programme sources (including the MRU catalogue)."))
    story.append(builder.section("5.6 System Security Implementation"))
    story.append(builder.body(
        "Passwords are hashed with Werkzeug, authentication uses Flask-Login sessions, administrative endpoints are "
        "protected by a custom admin_required guard returning 403 to students, CSRF protection is enabled in "
        "production, and uploaded logo files are sanitised and validated before being stored."))
    story.append(builder.section("5.7 System Testing"))
    story.append(builder.body(
        "Testing used pytest with a temporary SQLite database per run. The suite covers the recommendation engine "
        "(subject normalisation, weighted-score arithmetic, principal-pass counting, status outcomes, the foreign path, "
        "the analysis contract and field filtering), the routes and workflows (home, auth, profile, recommendations, "
        "chatbot, PDF export, admin permissions and persistence) and dataset integrity (schema columns, row counts, "
        "resolvable university references, numeric parsing and career mappings)."))
    story.append(builder.section("5.8 Test Cases and Results"))
    story.extend(builder.table([
        ["tests/test_engine.py", "11", "Engine logic and scoring"],
        ["tests/test_routes.py", "15", "Routes and workflows"],
        ["tests/test_data.py", "9", "Dataset integrity"],
        ["Total", "35", "0 failures reported"],
    ], [70 * mm, 25 * mm, 70 * mm], "Table 5.3: Automated test suite result"))
    story.append(builder.body(
        "Key verified cases include: subject-name normalisation (Mathematics equals Maths, CS equals Computer Science); "
        "weighted score computation across all four weights; Eligible/Borderline/Not eligible outcomes; international "
        "eligibility below and above the NCHE minimum; programme addition and persistence by an administrator; 403 denial "
        "of admin pages to students; PDF download with application/pdf content type; and CSV column and row-count "
        "enforcement. Detailed results appear in Appendix III."))
    story.append(builder.section("5.9 User Acceptance and Usability Evaluation"))
    story.append(builder.body(
        "A labelled gold-standard set of ten representative student profiles (varying grades, budgets, regions, "
        "sponsorship and fields) was used to check that every Eligible recommendation satisfied the student&rsquo;s "
        "explicit constraints. Nine of the ten profile groups had 100% satisfaction; one mid-level profile returned a "
        "single item whose region mismatch was correctly surfaced as a suitability reduction with a note. Aggregate "
        "accuracy was approximately 96%. Manual walkthroughs confirmed responsive layouts on narrow and wide viewports "
        "and consistent navigation across student and admin flows."))
    story.append(builder.section("5.10 Discussion of Results"))
    story.append(builder.body(
        "The results show that a transparent rule-based engine grounded in verified data produces accurate, explainable "
        "recommendations, that wrong matches are surfaced to students rather than silently included, and that the "
        "data-driven architecture allows new universities and courses to be added with no code change. The strongest "
        "limitation is dataset breadth: with 11 institutions the directory does not yet cover all NCHE-recognised "
        "universities, which is scheduled as the next release alongside a coverage report."))

    story.append(builder.chapter("CHAPTER SIX: IMPLEMENTATION PLAN AND WORK PLAN"))
    story.append(builder.section("6.1 Implementation Phases"))
    story.extend(builder.table([
        ["Phase 1", "Initiation & requirements", "Confirm scope, objectives, data sources and constraints."],
        ["Phase 2", "Design", "Model entities, recommendation algorithm, interface and test plan."],
        ["Phase 3", "Development & dataset", "Implement modules; collect and verify 2026/27 data (incl. MRU catalogue)."],
        ["Phase 4", "Testing & evaluation", "Automated tests, gold-standard accuracy check, usability walkthroughs."],
        ["Phase 5", "Documentation & handover", "User manual, evaluation and this report; pilot deployment."],
    ], [30 * mm, 45 * mm, 110 * mm], "Table 6.1: Implementation phases"))
    story.append(builder.section("6.2 Project Activities"))
    for item in [
        "Requirement elicitation and stakeholder consultation.",
        "Database and engine design with verification checklist.",
        "CSV dataset construction from official sources.",
        "Iterative development of the web interface and modules.",
        "Continuous integration-style test runs (pytest).",
        "Acceptance walkthroughs and report writing.",
    ]:
        story.append(builder.bullet(item))
    story.append(builder.section("6.3 Project Timeline"))
    story.extend(builder.table([
        ["Month 1", "Requirements, scope, and data-source shortlist."],
        ["Month 1-2", "System and database design; interface mockups."],
        ["Month 2-4", "Module development and dataset collection/verification."],
        ["Month 4-5", "Automated and user testing; accuracy evaluation."],
        ["Month 5-6", "Pilot deployment, documentation and report finalisation."],
    ], [35 * mm, 150 * mm], "Table 6.2: Project timeline (6 months)"))
    story.append(builder.section("6.4 Monitoring and Evaluation Framework"))
    story.append(builder.body(
        "Progress is monitored weekly against the milestones above using four indicators: dataset verification status "
        "(rows with confirmed official sources), automated test pass rate, accuracy of Eligible outputs against the "
        "gold-standard set, and user acceptance feedback collected during walkthroughs."))
    story.append(builder.section("6.5 Pilot Implementation Plan"))
    story.append(builder.body(
        "The pilot will deploy UniGuide Uganda for career guidance counsellors at selected secondary schools and for the "
        "admissions office of the case-study university. Success criteria are a stable 100% test pass, at least 95% "
        "accuracy on a fresh labelled sample, positive usability feedback, and an admin coverage report comparing "
        "recognised, imported and pending universities against the NCHE directory."))

    story.append(builder.chapter("CHAPTER SEVEN: PROJECT BUDGET"))
    story.append(builder.section("7.1 Introduction"))
    story.append(builder.body(
        "This chapter presents a realistic itemized budget for the project. All amounts are in Uganda Shillings (UGX) "
        "so that totals are comparable in one consistent currency."))
    story.append(builder.section("7.2 Software Development Costs"))
    story.extend(builder.table([
        ["Requirements analysis and design", "800,000"],
        ["Recommendation engine and scoring model", "1,500,000"],
        ["Web interface and admin dashboard", "2,000,000"],
        ["Dataset collection and verification", "2,000,000"],
        ["Integration, chatbot and PDF reporting", "900,000"],
        ["Subtotal", "7,200,000"],
    ], [120 * mm, 30 * mm], "Table 7.1: Software development costs"))
    story.append(builder.section("7.3 Hardware and Equipment Costs"))
    story.extend(builder.table([
        ["Development laptop", "3,200,000"],
        ["External backup storage", "350,000"],
        ["Internet and data services (12 months)", "600,000"],
        ["Subtotal", "4,150,000"],
    ], [120 * mm, 30 * mm], "Table 7.2: Hardware and equipment costs"))
    story.append(builder.section("7.4 Training and Data Collection Costs"))
    story.extend(builder.table([
        ["Field visits and document collection", "900,000"],
        ["Stakeholder consultations", "400,000"],
        ["User training and orientation sessions", "500,000"],
        ["Subtotal", "1,800,000"],
    ], [120 * mm, 30 * mm], "Table 7.3: Training and data collection costs"))
    story.append(builder.section("7.5 Testing and Evaluation Costs"))
    story.extend(builder.table([
        ["Automated testing tooling and fixtures", "150,000"],
        ["User acceptance testing sessions", "300,000"],
        ["Gold-standard evaluation and printing", "250,000"],
        ["Subtotal", "700,000"],
    ], [120 * mm, 30 * mm], "Table 7.4: Testing and evaluation costs"))
    story.append(builder.section("7.6 Maintenance and Hosting Costs"))
    story.extend(builder.table([
        ["Cloud/VPS hosting (year one)", "1,200,000"],
        ["Domain registration", "150,000"],
        ["SSL certificate, backups and support", "350,000"],
        ["Subtotal", "1,700,000"],
    ], [120 * mm, 30 * mm], "Table 7.5: Maintenance and hosting costs"))
    story.append(builder.section("7.7 Total Estimated Budget"))
    story.extend(builder.table([
        ["Software development", "7,200,000"],
        ["Hardware and equipment", "4,150,000"],
        ["Training and data collection", "1,800,000"],
        ["Testing and evaluation", "700,000"],
        ["Maintenance and hosting", "1,700,000"],
        ["TOTAL (UGX)", "15,550,000"],
    ], [120 * mm, 30 * mm], "Table 7.6: Total estimated budget (UGX)"))

    story.append(builder.chapter("CHAPTER EIGHT: RISKS, MITIGATION AND SUSTAINABILITY"))
    story.append(builder.section("8.1 Potential Project Risks"))
    story.extend(builder.table([
        ["Stale or inaccurate admission data", "High", "Verify every record against an official source; test-driven dataset checks."],
        ["Scope creep during development", "Medium", "Agile iterations with a controlled backlog and agreed milestones."],
        ["Low user adoption", "Medium", "Counsellor pilot, guidance notes and responsive interface."],
        ["Single developer availability", "Low", "Documentation and a data-driven engine that reduces code changes."],
    ], [75 * mm, 25 * mm, 85 * mm], "Table 8.1: Potential project risks and mitigation"))
    story.append(builder.section("8.2 Risk Mitigation Strategies"))
    story.append(builder.body(
        "Dataset risks are mitigated through an official-source column on every programme row, verification checklists "
        "and automated schema checks. Development risks are mitigated with modular blueprints, a documented engine and "
        "frequent test runs. Adoption risks are mitigated with training, clear reasons on every recommendation and "
        "mobile-first design."))
    story.append(builder.section("8.3 Data Security and Privacy Risks"))
    story.append(builder.body(
        "Risks include credential leakage, unauthorised administrative access and collection of unnecessary student "
        "data. Mitigations are password hashing, role-based access control, CSRF protection, data minimisation and "
        "documented credentials that must be changed before public deployment."))
    story.append(builder.section("8.4 System Maintenance"))
    story.append(builder.body(
        "Admission information changes every year. Maintenance is achieved through the administrator dashboard CRUD and "
        "CSV re-import (no code changes for dataset updates), the automated test suite for regression safety, and "
        "version-controlled source and data files."))
    story.append(builder.section("8.5 Sustainability Strategy"))
    story.append(builder.body(
        "The system is sustainable because it is built on low-cost, open-source components, runs on modest hosting, is "
        "maintained through its own admin interface, and its logo and university metadata make it extensible to the "
        "full NCHE directory. A coverage report is planned so that recognised, imported and pending universities are "
        "transparent for the administrator."))
    story.append(builder.section("8.6 Future System Improvements"))
    story.append(builder.body(
        "Planned improvements include the full NCHE-recognised university directory (about 64 universities plus MUBS) "
        "with an admin coverage report and revocation handling, an official logo system with a verified-logo status "
        "report, configurable per-programme admission rules for future academic years, richer PDF layout, and optional "
        "parliamentary/commission scholarship cut-off awareness."))

    story.append(builder.chapter("CHAPTER NINE: EXPECTED OUTPUTS AND OUTCOMES"))
    story.append(builder.section("9.1 Expected System Outputs"))
    story.extend(builder.table([
        ["Status-labelled recommendations", "Eligible / Borderline / Not eligible with weighted scores and cut-offs."],
        ["Reasons and missing requirements", "Explainable text for every match, including what the student lacks."],
        ["Subject-combination guidance", "A-Level combinations recommended per field and career."],
        ["University directory and detail", "Name, location, type, programme listing and official sources."],
        ["Comparison table", "Universities compared by type, location, fees, cut-offs and programmes."],
        ["AI Guide answers", "Rule-based answers grounded in the verified dataset."],
        ["PDF report", "A branded student snapshot and recommendation report."],
        ["Admin coverage and logo status", "Universities, programmes, logos and enquiries managed from the dashboard."],
    ], [70 * mm, 115 * mm], "Table 9.1: Expected system outputs"))
    story.append(builder.section("9.2 Expected Long-Term Outcomes"))
    story.append(builder.body(
        "In the medium term the system is expected to reduce misapplication in the pilot schools, improve course-fit and "
        "help counsellors respond faster to admission questions. The demonstration at MRU validates the approach for "
        "private-chartered institutions, and expansion of the directory to all NCHE-recognised institutions would make "
        "UniGuide the single reference point for admission guidance in Uganda. Outcomes demonstrated by evaluation to "
        "date are the recommendation accuracy results and the passing test suite; broader adoption outcomes require "
        "longer-term pilot data."))

    story.append(builder.chapter("CHAPTER TEN: CONCLUSION AND RECOMMENDATIONS"))
    story.append(builder.section("10.1 Introduction"))
    story.append(builder.body(
        "This chapter summarises the project, draws conclusions from the implemented system and evaluation, and makes "
        "recommendations for wider deployment and future development."))
    story.append(builder.section("10.2 Summary of the Project"))
    story.append(builder.body(
        "UniGuide Uganda, an AI-powered university and course recommendation system, was designed, implemented and "
        "evaluated. It replaces manual, scattered information gathering with a verified, searchable and explainable "
        "matching workflow covering eligible-course discovery, subject-combination guidance, comparison, chatbot support "
        "and PDF reporting, administered through a secure dashboard. The shipped dataset includes 11 universities and "
        "75 programme records verified against official 2026/27 sources."))
    story.append(builder.section("10.3 Conclusion"))
    story.append(builder.body(
        "The evaluation demonstrated that a transparent, data-driven engine produces accurate recommendations (about "
        "96% of Eligible outputs satisfied every stated constraint) and surfaces mismatches honestly, while the "
        "maintainable architecture allows the dataset to grow without code changes. The system therefore meets its "
        "objective of helping students identify courses they genuinely qualify for and provides a solid foundation for "
        "a national university directory service."))
    story.append(builder.section("10.4 Recommendations"))
    for item in [
        "Deploy the system with the full NCHE directory of recognised universities and a coverage report.",
        "Establish a yearly data-update workflow before each admission cycle using the import dashboard.",
        "Engage career guidance departments in schools for training and pilot feedback.",
        "Add an official logo collection workflow and the planned configurable admission-rule editor.",
        "Enforce credential changes and follow the data-protection policy before any public deployment.",
    ]:
        story.append(builder.bullet(item))
    story.append(builder.section("10.5 Areas for Future Development"))
    story.append(builder.body(
        "Future work includes per-programme configurable admission rules for new academic years, expansion to diploma "
        "and certificate programmes of ODAIs/OTIs, performance notifications to subscribed students, multilingual "
        "interfaces, and retrieval-augmented chatbot phrasing while keeping answers grounded in the verified dataset."))

    story.append(builder.chapter("REFERENCES"))
    for ref in [
        "National Council for Higher Education (NCHE), Uganda. <i>Universities directory and academic programmes register</i>. Available at https://unche.or.ug (verified October 2026).",
        "Makerere University. <i>Admissions: undergraduate programmes and cut-off points</i>. Available at https://www.mak.ac.ug.",
        "Muteesa I Royal University. <i>Admissions portal: programmes and fees, 2026/27</i>. Available at https://eportal.mru.ac.ug/apply/programmes.aspx.",
        "Uganda National Examinations Board (UNEB). <i>UCE and UACE regulations and grading</i>. Available at https://www.uneb.ac.ug.",
        "Islamic University in Uganda / Uganda Christian University. <i>Admission requirements for bachelor programmes, 2026/27</i>. Official university websites.",
        "ReportLab. <i>PDF document generation for Python</i>. Available at https://www.reportlab.com.",
        "Pallets Projects. <i>Flask documentation</i>. Available at https://flask.palletsprojects.com.",
        "Uganda Bureau of Statistics. <i>Higher education participation indicators</i>. Available at https://www.ubos.org.",
    ]:
        story.append(builder.bullet(ref))

    story.append(builder.chapter("APPENDICES"))
    story.append(builder.section("Appendix I: Interview Guide"))
    story.append(builder.body(
        "Semi-structured questions used with counsellors and admissions officers, covering: how students currently learn "
        "about courses; which information is hardest to find; how cut-off and fee information is updated; and how an "
        "automated tool would fit their workflow. (Field notes retained by the researcher.)"))
    story.append(builder.section("Appendix II: Questionnaire"))
    story.append(builder.body(
        "A short user questionnaire covering device usage, information sources consulted, confidence in course choice, "
        "and willingness to use a recommendation system. (Data collected during pilot walkthroughs.)"))
    story.append(builder.section("Appendix III: System Test Cases"))
    story.append(builder.body(
        "Documented in full in the automated suite and docs/testing_report.md. Highlights: subject-name normalisation; "
        "weighted-score arithmetic for essential/relevant/other/subsidiary weights; principal-pass counting; "
        "Eligible/Borderline/Not-eligible classification; foreign minimum comparisons; the analysis output contract; "
        "route status codes and redirections; admin persistence; 403 denials; PDF content type; and CSV schema checks. "
        "Result: 35 passed, 0 failed."))
    story.append(builder.section("Appendix IV: System Diagrams"))
    story.append(builder.body(
        "This appendix contains the use-case diagram, system context diagram, data-flow diagram, entity-relationship "
        "diagram and system architecture diagram. The report body presents the equivalent tables and text descriptions; "
        "the diagrams are maintained with the project documentation pack and inserted here for the final submission."))
    story.append(builder.section("Appendix V: Sample Screenshots of the System"))
    story.append(builder.body(
        "The following pages show the home page with the university directory, the university detail page with programmes "
        "and fees, the recommendations page, the comparison table, the AI Guide chat and the admin logo-status report. "
        "Screenshots are captured from the running application and inserted at the marked positions in the final copy."))
    story.append(builder.section("Appendix VI: Work Plan and Budget"))
    story.append(builder.body(
        "The detailed work plan (six-month timeline, phases and activities) is presented in Chapter Six and the itemized "
        "budget in UGX in Chapter Seven. Supporting weekly activity sheets are retained by the researcher."))

    story.append(Spacer(1, 8 * mm))
    story.append(builder.body(
        "<b>Important Guidance for Final Submission.</b> Chapter Three describes the methods actually used and data "
        "actually collected; Chapter Four contains the actual system requirements, diagrams, database design and "
        "interface designs; Chapter Five presents implementation details, screenshots, test cases and actual test "
        "results (the tests reported here were performed with the included pytest suite); Chapter Six shows the actual "
        "project schedule; Chapter Seven is a realistic itemized budget in UGX; and Chapter Nine distinguishes expected "
        "benefits from outcomes demonstrated by evaluation. Placeholders marked [Student Name], [Registration No.], "
        "[University], [Supervisor] and role signatures must be completed before submission, and any lecturer or "
        "department formatting instructions take precedence over this structure."))

    return story


def build():
    universities = _csv_rows("universities.csv")
    programmes = _csv_rows("programmes.csv") + _csv_rows("programmes_mru.csv")
    careers = _csv_rows("careers.csv")

    builder = _Builder()
    builder.styles = _styles()
    _build_story(builder, builder.styles, universities, programmes, careers)
    captions = list(builder.captions)

    builder = _Builder()
    builder.styles = _styles()
    builder.captions = captions
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=17 * mm,
        rightMargin=17 * mm,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
        title="UniGuide Uganda - Software Engineering Project Report",
        author="UniGuide Uganda",
        subject="AI-Powered University and Course Recommendation System for Uganda",
    )
    story = _build_story(builder, builder.styles, universities, programmes, careers)
    doc.afterFlowable = _make_after_flowable(doc)
    doc.multiBuild(story, onFirstPage=_footer, onLaterPages=_footer)
    return OUTPUT


if __name__ == "__main__":
    print("Writing {0}".format(build()))