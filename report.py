import io
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

NAVY = colors.HexColor("#12345A")
GREEN = colors.HexColor("#18794E")
GOLD = colors.HexColor("#F4B942")
GREY = colors.HexColor("#F1F5F9")


def _styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "TitleX", parent=base["Title"], textColor=NAVY, fontSize=20, spaceAfter=4
        ),
        "subtitle": ParagraphStyle(
            "SubtitleX", parent=base["Normal"], textColor=colors.HexColor("#475569"), fontSize=10
        ),
        "h2": ParagraphStyle(
            "H2X", parent=base["Heading2"], textColor=NAVY, fontSize=13, spaceBefore=8, spaceAfter=4
        ),
        "body": ParagraphStyle("BodyX", parent=base["Normal"], fontSize=9, leading=12),
        "small": ParagraphStyle(
            "SmallX", parent=base["Normal"], fontSize=8, textColor=colors.HexColor("#64748B")
        ),
    }
    return styles


def _status_color(status):
    if status == "Eligible":
        return GREEN
    if status == "Borderline":
        return GOLD
    return colors.HexColor("#B91C1C")


def _sports_summary(data):
    level = data.get("sports_level")
    if not level:
        return "Not provided"
    details = data.get("sports_details")
    return "{0} level{1}".format(level, " ({0})".format(details) if details else "")


def build_pdf(results, profile, user):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="UniGuide Uganda - Recommendation Report",
    )
    styles = _styles()
    story = []

    story.append(Paragraph("UniGuide Uganda", styles["title"]))
    story.append(Paragraph("University & Course Recommendation Report for {0}".format(user.name), styles["subtitle"]))
    story.append(Paragraph(
        "Generated {0} &middot; Admission information for {1} &middot; Verify milestones with the university before applying.".format(
            datetime.now().strftime("%d %B %Y"),
            profile.data.get("preferred_field") or "all fields",
        ),
        styles["small"],
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Student Snapshot", styles["h2"]))
    d = profile.data
    snapshot = [
        ["Citizenship", "Ugandan" if d.get("citizenship") != "foreign" else "Foreign (International)"],
        ["Gender", d.get("gender") or "Not specified"],
        ["Academic record", d.get("uce_summary") or "Not provided"],
        ["Preferred area", d.get("preferred_field") or "Not selected"],
        ["Annual budget (UGX)", "{:,.0f}".format(d.get("budget")) if d.get("budget") else "Not provided"],
        ["Preferred region", d.get("preferred_region") or "Any"],
        ["Sponsorship", "Government" if d.get("sponsorship_pref") == "government" else "Private"],
        ["Sports", _sports_summary(d)],
    ]
    snapshot_table = Table(snapshot, colWidths=[55 * mm, 120 * mm])
    snapshot_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), GREY),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(snapshot_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Recommended Programmes", styles["h2"]))
    for item in results:
        p = item["programme"]
        heading = "{0} - {1}".format(p.name, item["university"].name)
        story.append(Paragraph(
            heading + " &nbsp; <font color='{0}'><b>[{1}]</b></font>".format(
                "#18794E" if item["status"] == "Eligible" else ("#F4B942" if item["status"] == "Borderline" else "#B91C1C"),
                item["status"],
            ),
            styles["body"],
        ))
        details = []
        if item["score"] is not None:
            details.append("Weighted score / total: {0}".format(item["score"]))
        if item["cutoff"] is not None:
            details.append("Required cut-off: {0}".format(item["cutoff"]))
        if item["tuition"] not in (None, ""):
            details.append("Tuition (UGX/year): {0:,.0f}".format(item["tuition"]))
        details.append("Duration: {0} years".format(p.duration_years))
        details.append("Admission year: {0}".format(item["admission_year"]))
        story.append(Paragraph(" &bull; ".join(details), styles["small"]))
        for reason in item["reasons"]:
            story.append(Paragraph("&middot; {0}".format(reason), styles["small"]))
        for note in item["missing"]:
            story.append(Paragraph("<font color='red'>&middot; {0}</font>".format(note), styles["small"]))
        source = item["official_source"] or "Official university website"
        story.append(Paragraph("Source: {0}".format(source), styles["small"]))
        story.append(Spacer(1, 5))

    story.append(Spacer(1, 6))
    note = Paragraph(
        "Cut-off points differ by university, programme, sponsorship scheme and admission year. "
        "This report uses verified admission information from official 2026/27 documents where available. "
        "Always confirm your eligibility with the university admissions office before applying.",
        styles["small"],
    )
    story.append(note)

    doc.build(story)
    buffer.seek(0)
    return buffer