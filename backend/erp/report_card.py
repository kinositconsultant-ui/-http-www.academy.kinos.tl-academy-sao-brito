"""PDF report card generation using ReportLab.

No system dependencies (unlike WeasyPrint). Produces a one-page A4 report
card that summarises a student's grades, attendance, and pass/fail status
for a given academic year.
"""
from io import BytesIO
from collections import defaultdict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether,
)


# Brand palette (matches the Tailwind look used in the rest of the app)
BRAND = colors.HexColor("#2563eb")        # blue-600
INK = colors.HexColor("#18181b")          # zinc-900
MUTED = colors.HexColor("#71717a")        # zinc-500
LINE = colors.HexColor("#e4e4e7")         # zinc-200
SOFT = colors.HexColor("#f4f4f5")         # zinc-100
PASS_BG = colors.HexColor("#ecfdf5")
PASS_FG = colors.HexColor("#047857")
FAIL_BG = colors.HexColor("#fef2f2")
FAIL_FG = colors.HexColor("#b91c1c")


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName="Helvetica-Bold",
                                fontSize=18, leading=22, textColor=INK, spaceAfter=2),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName="Helvetica",
                                   fontSize=9, leading=12, textColor=MUTED),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold",
                             fontSize=11, leading=14, textColor=INK,
                             spaceBefore=10, spaceAfter=6),
        "label": ParagraphStyle("label", parent=base["Normal"], fontName="Helvetica",
                                fontSize=7.5, textColor=MUTED, leading=10),
        "value": ParagraphStyle("value", parent=base["Normal"], fontName="Helvetica-Bold",
                                fontSize=10, leading=13, textColor=INK),
        "muted": ParagraphStyle("muted", parent=base["Normal"], fontName="Helvetica",
                                fontSize=8.5, textColor=MUTED, leading=11),
        "small": ParagraphStyle("small", parent=base["Normal"], fontName="Helvetica",
                                fontSize=8.5, textColor=INK, leading=11),
    }


def _header(school, styles, year_label):
    title = school.name if school else "Academy ERP"
    subtitle_parts = []
    if school and school.motto:
        subtitle_parts.append(f"<i>{school.motto}</i>")
    if school and school.address:
        subtitle_parts.append(school.address)
    if school and school.phone:
        subtitle_parts.append(school.phone)
    subtitle = " · ".join(subtitle_parts) or "Academy ERP"

    band = Table(
        [[Paragraph(title, styles["title"]),
          Paragraph(f"<b>REPORT CARD</b><br/>{year_label}", styles["value"])]],
        colWidths=[120 * mm, 60 * mm],
    )
    band.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 1.2, BRAND),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return [band, Paragraph(subtitle, styles["subtitle"]), Spacer(1, 8)]


def _student_block(student, styles):
    cells = [
        [Paragraph("STUDENT", styles["label"]),
         Paragraph(student.full_name, styles["value"])],
        [Paragraph("ADMISSION NO.", styles["label"]),
         Paragraph(student.admission_no, styles["value"])],
        [Paragraph("CLASS", styles["label"]),
         Paragraph(str(student.school_class) if student.school_class else "—",
                   styles["value"])],
        [Paragraph("DATE OF BIRTH", styles["label"]),
         Paragraph(student.date_of_birth.isoformat() if student.date_of_birth else "—",
                   styles["value"])],
        [Paragraph("PARENT / GUARDIAN", styles["label"]),
         Paragraph(student.parent_name or "—", styles["value"])],
        [Paragraph("CONTACT", styles["label"]),
         Paragraph(student.parent_phone or student.parent_email or "—",
                   styles["value"])],
    ]
    # 2 columns wide, 3 rows
    rows = [cells[i:i + 2] for i in range(0, len(cells), 2)]
    flat = []
    for r in rows:
        line = []
        for pair in r:
            line.extend(pair)
        flat.append(line)
    tbl = Table(flat, colWidths=[28 * mm, 60 * mm, 28 * mm, 60 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tbl


def _semester_grade_table(grades, styles, semester_label):
    head = ["Subject", "Exam", "Score", "%", "Grade", "Status"]
    data = [head]
    total_pct = 0
    for g in grades:
        data.append([
            g.subject.name,
            g.exam_name,
            f"{g.score} / {g.total}",
            f"{g.percentage}%",
            g.letter,
            "PASS" if g.is_pass else "FAIL",
        ])
        total_pct += g.percentage
    avg = round(total_pct / len(grades), 2) if grades else 0
    data.append(["", "", "", "Average", f"{avg}%", ""])

    tbl = Table(data, colWidths=[55 * mm, 45 * mm, 25 * mm, 18 * mm, 15 * mm, 18 * mm])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, INK),
        ("ALIGN", (2, 1), (-1, -1), "CENTER"),
        ("ALIGN", (0, 1), (1, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, SOFT]),
        ("FONTNAME", (3, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.5, LINE),
    ]
    # Colour the Status cell per row
    for i, g in enumerate(grades, start=1):
        if g.is_pass:
            style += [("BACKGROUND", (5, i), (5, i), PASS_BG),
                      ("TEXTCOLOR", (5, i), (5, i), PASS_FG),
                      ("FONTNAME", (5, i), (5, i), "Helvetica-Bold")]
        else:
            style += [("BACKGROUND", (5, i), (5, i), FAIL_BG),
                      ("TEXTCOLOR", (5, i), (5, i), FAIL_FG),
                      ("FONTNAME", (5, i), (5, i), "Helvetica-Bold")]
    tbl.setStyle(TableStyle(style))
    return KeepTogether([
        Paragraph(f"<b>{semester_label}</b>", styles["h2"]),
        tbl,
    ])


def _summary_block(passed_count, failed_count, total_avg, attendance_rate, styles):
    cells = [[
        Paragraph("OVERALL AVERAGE", styles["label"]),
        Paragraph("SUBJECTS PASSED", styles["label"]),
        Paragraph("SUBJECTS FAILED", styles["label"]),
        Paragraph("ATTENDANCE", styles["label"]),
    ], [
        Paragraph(f"{total_avg}%", styles["value"]),
        Paragraph(str(passed_count), styles["value"]),
        Paragraph(str(failed_count), styles["value"]),
        Paragraph(f"{attendance_rate}%" if attendance_rate is not None else "—",
                  styles["value"]),
    ]]
    tbl = Table(cells, colWidths=[42 * mm] * 4)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return tbl


def _footer(styles):
    sig = Table([
        [Paragraph("___________________________<br/>Class Teacher",
                   styles["small"]),
         Paragraph("___________________________<br/>Principal",
                   styles["small"]),
         Paragraph("___________________________<br/>Parent / Guardian",
                   styles["small"])]
    ], colWidths=[60 * mm] * 3)
    sig.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("TOPPADDING", (0, 0), (-1, -1), 20),
    ]))
    return sig


def build_report_card(student, grades, school, academic_year, attendance_stats):
    """Build the PDF and return raw bytes.

    `grades` is an iterable already filtered to the chosen academic year.
    `attendance_stats` is a dict {present, total} or None.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm,
                            title=f"Report Card - {student.full_name}",
                            author=school.name if school else "Academy ERP")
    styles = _styles()
    year_label = academic_year.name if academic_year else "All Years"

    # Group grades by semester
    by_sem = defaultdict(list)
    for g in grades:
        by_sem[g.semester].append(g)

    sem_order = [code for code, _ in __import__("erp").models.Grade.SEMESTER_CHOICES]
    sem_labels = dict(__import__("erp").models.Grade.SEMESTER_CHOICES)

    # Overall stats
    flat = list(grades)
    if flat:
        avg = round(sum(g.percentage for g in flat) / len(flat), 2)
        passed = sum(1 for g in flat if g.is_pass)
        failed = sum(1 for g in flat if not g.is_pass)
    else:
        avg, passed, failed = 0, 0, 0

    att_rate = None
    if attendance_stats and attendance_stats.get("total"):
        att_rate = round(100 * attendance_stats["present"] / attendance_stats["total"], 1)

    story = []
    story += _header(school, styles, year_label)
    story.append(_student_block(student, styles))
    story.append(Spacer(1, 10))
    story.append(_summary_block(passed, failed, avg, att_rate, styles))

    if not flat:
        story.append(Spacer(1, 14))
        story.append(Paragraph(
            "<i>No grades recorded for this academic year yet.</i>",
            styles["muted"]))
    else:
        for sem_code in sem_order:
            sem_grades = by_sem.get(sem_code, [])
            if not sem_grades:
                continue
            story.append(Spacer(1, 6))
            story.append(_semester_grade_table(sem_grades, styles, sem_labels[sem_code]))

    # Overall verdict
    story.append(Spacer(1, 14))
    if failed == 0 and passed > 0:
        verdict_text = ("<b>RESULT:</b> &nbsp; <font color='#047857'>"
                        "PROMOTED — all subjects passed.</font>")
    elif failed > 0:
        verdict_text = (f"<b>RESULT:</b> &nbsp; <font color='#b91c1c'>"
                        f"FAILED — {failed} subject(s) below passing mark.</font>")
    else:
        verdict_text = ("<b>RESULT:</b> &nbsp; "
                        "<font color='#71717a'>Pending — no grades on file.</font>")
    story.append(Paragraph(verdict_text, styles["value"]))

    story.append(Spacer(1, 24))
    story.append(_footer(styles))

    doc.build(story)
    pdf = buf.getvalue()
    buf.close()
    return pdf
