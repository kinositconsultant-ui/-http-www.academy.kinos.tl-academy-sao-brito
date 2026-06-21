"""PDF generation for fee invoices and payment receipts using ReportLab.

Returns raw PDF bytes. Re-uses the brand palette from report_card.py so
all PDFs share a consistent look.
"""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)


BRAND = colors.HexColor("#2563eb")
INK = colors.HexColor("#18181b")
MUTED = colors.HexColor("#71717a")
LINE = colors.HexColor("#e4e4e7")
SOFT = colors.HexColor("#f4f4f5")
PAID_BG = colors.HexColor("#ecfdf5")
PAID_FG = colors.HexColor("#047857")
OVERDUE_BG = colors.HexColor("#fef2f2")
OVERDUE_FG = colors.HexColor("#b91c1c")


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=base["Title"], fontName="Helvetica-Bold",
                                fontSize=20, leading=24, textColor=INK, spaceAfter=2),
        "subtitle": ParagraphStyle("st", parent=base["Normal"], fontName="Helvetica",
                                   fontSize=9, leading=12, textColor=MUTED),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold",
                             fontSize=11, leading=14, textColor=INK,
                             spaceBefore=10, spaceAfter=6),
        "label": ParagraphStyle("l", parent=base["Normal"], fontName="Helvetica",
                                fontSize=7.5, textColor=MUTED, leading=10),
        "value": ParagraphStyle("v", parent=base["Normal"], fontName="Helvetica-Bold",
                                fontSize=10, leading=13, textColor=INK),
        "big_num": ParagraphStyle("n", parent=base["Normal"], fontName="Helvetica-Bold",
                                  fontSize=18, leading=20, textColor=BRAND),
        "muted": ParagraphStyle("m", parent=base["Normal"], fontName="Helvetica",
                                fontSize=8.5, textColor=MUTED, leading=11),
        "small": ParagraphStyle("s", parent=base["Normal"], fontName="Helvetica",
                                fontSize=8.5, textColor=INK, leading=11),
    }


def _header(school, styles, document_kind, doc_id):
    title = school.name if school else "Academy ERP"
    bits = []
    if school and school.motto:
        bits.append(f"<i>{school.motto}</i>")
    if school and school.address:
        bits.append(school.address)
    if school and school.phone:
        bits.append(school.phone)
    if school and school.email:
        bits.append(school.email)
    subtitle = " · ".join(bits) or "Academy ERP"

    band = Table(
        [[Paragraph(title, styles["title"]),
          Paragraph(f"<b>{document_kind}</b><br/>#{doc_id}", styles["value"])]],
        colWidths=[120 * mm, 60 * mm],
    )
    band.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 1.4, BRAND),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return [band, Paragraph(subtitle, styles["subtitle"]), Spacer(1, 10)]


def _student_block(student, styles):
    cells = [
        [Paragraph("BILLED TO", styles["label"]),
         Paragraph(student.full_name, styles["value"])],
        [Paragraph("ADMISSION", styles["label"]),
         Paragraph(student.admission_no, styles["value"])],
        [Paragraph("CLASS", styles["label"]),
         Paragraph(str(student.school_class) if student.school_class else "—",
                   styles["value"])],
        [Paragraph("PARENT", styles["label"]),
         Paragraph(student.father_name or student.mother_name or "—",
                   styles["value"])],
        [Paragraph("EMAIL", styles["label"]),
         Paragraph(student.parent_email or "—", styles["small"])],
        [Paragraph("PHONE", styles["label"]),
         Paragraph(student.parent_phone or "—", styles["small"])],
    ]
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


def _money(amount, currency):
    return f"{currency} {float(amount or 0):,.2f}"


def build_invoice_pdf(invoice, school):
    """One-page invoice PDF with line item + payment summary."""
    from .pdf_brand import header_block, make_footer_callback
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=22 * mm,
                            title=f"Invoice #{invoice.id}",
                            author=school.name if school else "Academy ERP")
    styles = _styles()
    currency = (school.currency if school else "USD") or "USD"
    story = []
    story += header_block(school, "INVOICE", f"#{invoice.id}")
    story.append(_student_block(invoice.student, styles))
    story.append(Spacer(1, 10))

    # Invoice meta
    meta = Table([[
        Paragraph("ISSUED", styles["label"]),
        Paragraph(str(invoice.issued_date), styles["value"]),
        Paragraph("DUE", styles["label"]),
        Paragraph(str(invoice.due_date), styles["value"]),
        Paragraph("STATUS", styles["label"]),
        Paragraph(invoice.get_status_display().upper(), styles["value"]),
    ]], colWidths=[20 * mm, 30 * mm, 18 * mm, 30 * mm, 22 * mm, 36 * mm])
    status_bg = (PAID_BG if invoice.status == "paid"
                 else OVERDUE_BG if invoice.status == "overdue" else SOFT)
    status_fg = (PAID_FG if invoice.status == "paid"
                 else OVERDUE_FG if invoice.status == "overdue" else INK)
    meta.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("BACKGROUND", (5, 0), (5, 0), status_bg),
        ("TEXTCOLOR", (5, 0), (5, 0), status_fg),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta)
    story.append(Spacer(1, 12))

    # Line items table
    rows = [["#", "Description", "Amount"], ["1", invoice.title, _money(invoice.amount, currency)]]
    items = Table(rows, colWidths=[15 * mm, 130 * mm, 35 * mm])
    items.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, INK),
        ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
    ]))
    story.append(items)

    if invoice.notes:
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"<i>Notes: {invoice.notes}</i>", styles["muted"]))

    # Totals
    story.append(Spacer(1, 16))
    totals = Table([
        ["Subtotal", _money(invoice.amount, currency)],
        ["Paid to date", _money(invoice.amount_paid, currency)],
        ["Balance due", _money(invoice.balance, currency)],
    ], colWidths=[140 * mm, 40 * mm])
    totals.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, INK),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 12),
        ("TEXTCOLOR", (-1, -1), (-1, -1), BRAND),
    ]))
    story.append(totals)

    # Payments
    if invoice.payments.exists():
        story.append(Spacer(1, 18))
        story.append(Paragraph("Payment history", styles["h2"]))
        pay_rows = [["Date", "Method", "Reference", "Amount"]]
        for p in invoice.payments.all():
            pay_rows.append([str(p.paid_on), p.get_method_display(),
                             p.reference or "—", _money(p.amount, currency)])
        tbl = Table(pay_rows, colWidths=[28 * mm, 38 * mm, 70 * mm, 44 * mm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), SOFT),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, INK),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
        ]))
        story.append(tbl)

    story.append(Spacer(1, 24))
    story.append(Paragraph(
        "Please pay the balance due before the due date to avoid late penalties. "
        "Bank details and online payment links are available on your parent portal.",
        styles["muted"]))

    doc.build(story, onFirstPage=make_footer_callback(school),
              onLaterPages=make_footer_callback(school))
    return buf.getvalue()


def build_receipt_pdf(payment, invoice, school):
    """One-page payment receipt PDF."""
    from .pdf_brand import header_block, make_footer_callback
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=22 * mm,
                            title=f"Receipt PMT-{payment.id}",
                            author=school.name if school else "Academy ERP")
    styles = _styles()
    currency = (school.currency if school else "USD") or "USD"

    story = []
    story += header_block(school, "PAYMENT RECEIPT", f"PMT-{payment.id}")
    story.append(_student_block(invoice.student, styles))
    story.append(Spacer(1, 12))

    # Big amount banner
    banner = Table([[
        Paragraph("AMOUNT RECEIVED", styles["label"]),
        Paragraph(_money(payment.amount, currency), styles["big_num"]),
    ]], colWidths=[60 * mm, 120 * mm])
    banner.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), PAID_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, PAID_FG),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(banner)
    story.append(Spacer(1, 14))

    info = Table([
        ["Invoice", f"#{invoice.id} — {invoice.title}"],
        ["Payment date", str(payment.paid_on)],
        ["Method", payment.get_method_display()],
        ["Reference", payment.reference or "—"],
        ["Received by", payment.received_by.get_full_name() if payment.received_by else "—"],
        ["Invoice balance after", _money(invoice.balance, currency)],
    ], colWidths=[55 * mm, 125 * mm])
    info.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, LINE),
    ]))
    story.append(info)

    story.append(Spacer(1, 24))
    story.append(Paragraph(
        "Thank you for your payment. Please retain this receipt for your records. "
        "If you spot any discrepancy, contact the school office quoting the receipt "
        f"number <b>PMT-{payment.id}</b>.",
        styles["muted"]))

    doc.build(story, onFirstPage=make_footer_callback(school),
              onLaterPages=make_footer_callback(school))
    return buf.getvalue()
