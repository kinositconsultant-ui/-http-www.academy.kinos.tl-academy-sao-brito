"""Shared PDF branding helpers — logo header + address/contact footer.

Use this from every PDF builder so all institutional PDFs share the same
look. Logo lives at backend/static/img/isjb-logo.jpg.
"""
from pathlib import Path

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, Table, TableStyle, Image, Spacer


BRAND = colors.HexColor("#b91c1c")   # red-700, ISJB house colour
INK = colors.HexColor("#18181b")
MUTED = colors.HexColor("#71717a")
ACCENT = colors.HexColor("#d97706")  # amber-600 — used for motto


def _logo_path():
    p = Path(settings.BASE_DIR) / "static" / "img" / "isjb-logo.jpg"
    return str(p) if p.exists() else None


def header_block(school, doc_title, doc_id, height_mm=18):
    """Return a list of Flowables: [logo + title row, contact subline, spacer]."""
    base = getSampleStyleSheet()
    school_style = ParagraphStyle(
        "PdfSchool", parent=base["Normal"], fontName="Helvetica-Bold",
        fontSize=11, leading=13, textColor=INK)
    motto_style = ParagraphStyle(
        "PdfMotto", parent=base["Normal"], fontName="Helvetica-Oblique",
        fontSize=7.5, leading=10, textColor=ACCENT)
    doc_style = ParagraphStyle(
        "PdfDoc", parent=base["Normal"], fontName="Helvetica-Bold",
        fontSize=10, leading=12, textColor=BRAND, alignment=2)  # right
    name = (school.name if school else "Instituto São João de Brito")
    motto = (school.motto if school else "Educar para Servir") or "Educar para Servir"

    logo = _logo_path()
    logo_flow = Image(logo, width=height_mm * mm, height=height_mm * mm) if logo else Paragraph("", school_style)

    left = Table([[logo_flow,
                   [Paragraph(name, school_style),
                    Paragraph(f"<i>{motto}</i>", motto_style)]]],
                 colWidths=[height_mm * mm + 4 * mm, None])
    left.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))

    head = Table([[left,
                   Paragraph(f"<b>{doc_title.upper()}</b><br/>{doc_id}", doc_style)]],
                 colWidths=[120 * mm, 60 * mm])
    head.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 1.4, BRAND),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [head, Spacer(1, 8)]


def footer_canvas(canvas, doc, school):
    """Draw the address + contact strip at the bottom of every page."""
    canvas.saveState()
    width = doc.pagesize[0]
    bottom = 10 * mm
    # 1px red rule
    canvas.setStrokeColor(BRAND)
    canvas.setLineWidth(0.8)
    canvas.line(12 * mm, bottom + 9 * mm, width - 12 * mm, bottom + 9 * mm)

    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    addr = (school.address if school and school.address
            else "Kasait, Ulmera, Bazartete, Liquiça, Timor-Leste")
    phone = (school.phone if school and school.phone else "+670 7775 4142")
    email = (school.email if school and school.email else "info@isjb.edu.tl")
    canvas.drawString(12 * mm, bottom + 5 * mm, addr)
    canvas.drawString(12 * mm, bottom + 1.5 * mm,
                      f"Tel: {phone}   ·   Email: {email}")
    # Page number on the right
    page = canvas.getPageNumber()
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.setFillColor(INK)
    canvas.drawRightString(width - 12 * mm, bottom + 1.5 * mm,
                           f"Page {page}")
    canvas.restoreState()


def make_footer_callback(school):
    """Return a (canvas, doc) callback bound to this school for build()."""
    def _cb(canvas, doc):
        footer_canvas(canvas, doc, school)
    return _cb
