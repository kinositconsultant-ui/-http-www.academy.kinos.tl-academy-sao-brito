"""Payslip PDF generator (per SalaryPayment row)."""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


BRAND = colors.HexColor("#b91c1c")
INK = colors.HexColor("#18181b")
MUTED = colors.HexColor("#71717a")
SOFT = colors.HexColor("#f4f4f5")
LINE = colors.HexColor("#e4e4e7")
PAID_BG = colors.HexColor("#ecfdf5")
PAID_FG = colors.HexColor("#047857")


def build_payslip_pdf(payslip, school):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm,
                            title=f"Payslip {payslip.id}",
                            author=school.name if school else "Academy ERP")

    base = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=base["Title"], fontName="Helvetica-Bold",
                        fontSize=20, leading=24, textColor=INK, spaceAfter=2)
    sub = ParagraphStyle("sub", parent=base["Normal"], fontName="Helvetica",
                         fontSize=9, leading=12, textColor=MUTED)
    label = ParagraphStyle("l", parent=base["Normal"], fontName="Helvetica",
                           fontSize=7.5, textColor=MUTED, leading=10)
    value = ParagraphStyle("v", parent=base["Normal"], fontName="Helvetica-Bold",
                           fontSize=10, leading=13, textColor=INK)
    muted = ParagraphStyle("m", parent=base["Normal"], fontName="Helvetica",
                           fontSize=8.5, textColor=MUTED, leading=11)

    currency = (school.currency if school else "USD") or "USD"

    def money(v):
        return f"{currency} {float(v or 0):,.2f}"
    t = payslip.teacher

    story = []
    # Header
    bits = []
    if school:
        if school.motto:
            bits.append(f"<i>{school.motto}</i>")
        if school.address:
            bits.append(school.address)
        if school.phone:
            bits.append(school.phone)
        if school.email:
            bits.append(school.email)
    band = Table([[Paragraph(school.name if school else "Academy ERP", h1),
                   Paragraph(f"<b>PAYSLIP</b><br/>{payslip.month}", value)]],
                 colWidths=[120 * mm, 50 * mm])
    band.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 1.4, BRAND),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(band)
    story.append(Paragraph(" · ".join(bits) or "Academy ERP", sub))
    story.append(Spacer(1, 12))

    # Employee block
    emp = Table([
        [Paragraph("EMPLOYEE", label), Paragraph(t.full_name, value),
         Paragraph("EMPLOYEE NO.", label), Paragraph(t.employee_no, value)],
        [Paragraph("ROLE", label),
         Paragraph(t.specialization or t.qualification or "Teacher", value),
         Paragraph("PAY PERIOD", label), Paragraph(payslip.month, value)],
        [Paragraph("STATUS", label),
         Paragraph(payslip.get_status_display().upper(), value),
         Paragraph("PAID ON", label),
         Paragraph(str(payslip.paid_date) if payslip.paid_date else "—", value)],
    ], colWidths=[28 * mm, 56 * mm, 28 * mm, 56 * mm])
    emp.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(emp)
    story.append(Spacer(1, 14))

    # Earnings / deductions split
    gross = float(payslip.amount or 0) + float(payslip.bonus or 0)
    net = gross - float(payslip.deductions or 0)
    rows = [
        ["Earnings", "", "Deductions", ""],
        ["Basic salary", money(payslip.amount), "Total deductions", money(payslip.deductions)],
        ["Bonus / allowances", money(payslip.bonus), "", ""],
        ["Gross", money(gross), "Net payable", money(net)],
    ]
    tbl = Table(rows, colWidths=[40 * mm, 40 * mm, 40 * mm, 40 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (1, 0), INK),
        ("BACKGROUND", (2, 0), (3, 0), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, INK),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (2, -1), (3, -1), PAID_BG),
        ("TEXTCOLOR", (3, -1), (3, -1), PAID_FG),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tbl)

    if payslip.note:
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"<i>Note: {payslip.note}</i>", muted))

    story.append(Spacer(1, 22))
    story.append(Paragraph(
        "This is a system-generated payslip. Please keep it for your records. "
        "Any discrepancies must be reported to HR within 7 days of receipt.",
        muted))

    doc.build(story)
    return buf.getvalue()
