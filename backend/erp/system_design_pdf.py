"""Branded PDF export of the System Design document.

Uses the shared `pdf_brand.py` header/footer so the document carries the
same logo + address + contact strip as every other institutional PDF.
"""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Preformatted, PageBreak, KeepTogether,
)

from .pdf_brand import header_block, make_footer_callback


INK = colors.HexColor("#18181b")
MUTED = colors.HexColor("#52525b")
SOFT = colors.HexColor("#f4f4f5")
LINE = colors.HexColor("#e4e4e7")
ACCENT = colors.HexColor("#b91c1c")
GREEN = colors.HexColor("#047857")
AMBER = colors.HexColor("#b45309")


def _styles():
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName="Helvetica-Bold",
                             fontSize=14, leading=18, textColor=ACCENT, spaceBefore=8,
                             spaceAfter=6),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold",
                             fontSize=11, leading=14, textColor=INK, spaceBefore=8,
                             spaceAfter=4),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName="Helvetica",
                               fontSize=9.5, leading=13, textColor=INK, spaceAfter=4),
        "muted": ParagraphStyle("muted", parent=base["BodyText"], fontName="Helvetica",
                                fontSize=8.5, leading=11, textColor=MUTED),
        "code": ParagraphStyle("code", parent=base["Code"], fontName="Courier",
                               fontSize=7.5, leading=9, textColor=INK,
                               backColor=SOFT, borderColor=LINE, borderWidth=0.5,
                               borderPadding=4),
        "td": ParagraphStyle("td", parent=base["BodyText"], fontName="Helvetica",
                             fontSize=8.5, leading=11, textColor=INK),
        "th": ParagraphStyle("th", parent=base["BodyText"], fontName="Helvetica-Bold",
                             fontSize=8.5, leading=11, textColor=colors.white),
    }


def _ipo_table(rows, st, widths=(40 * mm, 55 * mm, 55 * mm, 50 * mm)):
    """Render an Input-Process-Output table. First row = header."""
    data = [[Paragraph(c, st["th"]) for c in rows[0]]]
    for r in rows[1:]:
        data.append([Paragraph(c, st["td"]) for c in r])
    tbl = Table(data, colWidths=widths[:len(rows[0])], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
        ("BOX", (0, 0), (-1, -1), 0.4, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tbl


def _diagram(text, st):
    pre = Preformatted(text, st["code"])
    return KeepTogether([pre, Spacer(1, 4)])


def build_system_design_pdf(school):
    """Build the System Design PDF and return raw bytes."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=22 * mm,
        title="System Design — Academy & Finance ERP",
        author=school.name if school else "Academy ERP",
    )
    st = _styles()
    story = []
    story += header_block(school, "SYSTEM DESIGN", "Academy & Finance ERP")

    story.append(Paragraph(
        "<b>Document purpose:</b> a one-stop reference describing the architecture, "
        "user roles, data flows (Input → Process → Output) and operational artefacts "
        "of the Instituto São João de Brito Academy & Finance ERP. Suitable for "
        "demos, stakeholder review and onboarding new staff or developers.",
        st["muted"]))
    story.append(Spacer(1, 6))

    # --- 1. Architecture ---
    story.append(Paragraph("1 · High-Level Architecture", st["h1"]))
    story.append(_diagram(
        " Browser (Admin · Principal · Accountant · HR · Teacher · Parent · Student)\n"
        "       │  HTTPS (session + CSRF)\n"
        "       ▼\n"
        " Kubernetes Ingress  →  /api/*  → Django (uvicorn :8001)\n"
        "                        /*      → static redirect (React bypassed)\n"
        "       │\n"
        "       ▼\n"
        " Django 5.0.6 apps:  accounts · erp · portal · teacher · hr\n"
        "       │\n"
        "  ┌────┴────┬─────────────┬───────────────┐\n"
        "  ▼         ▼             ▼               ▼\n"
        " SQLite   /media       Stripe API     SendGrid API\n"
        " (data)   (uploads)   (LIVE test)    (MOCKED — wire key)\n",
        st))
    story.append(Paragraph(
        "Stack: Django · Django Templates · Tailwind (locally built) · "
        "Chart.js · ReportLab (PDF) · emergentintegrations (Stripe) · "
        "SendGrid SDK (gated by env vars).", st["body"]))

    # --- 2. Auth & role routing ---
    story.append(Paragraph("2 · Authentication & Role Routing", st["h1"]))
    story.append(_diagram(
        " POST /api/login/  →  Django session + CSRF  →  role lookup on User\n"
        "                          │\n"
        " ┌──────────┬─────────────┼─────────────┬──────────┬──────────┐\n"
        " ▼          ▼             ▼             ▼          ▼          ▼\n"
        " Admin   Principal    Accountant   HR / Teacher  Parent   Student\n"
        " /api/   /api/        /api/        /api/hr/     /api/    /api/\n"
        " dashboard dashboard  reports/     /api/teacher parent/  student/\n",
        st))

    # --- 3. Core IPO table ---
    story.append(Paragraph("3 · Core Domain — Input · Process · Output", st["h1"]))
    story.append(_ipo_table([
        ["Module", "Input", "Process", "Output"],
        ["School Profile",
         "Name, motto, address, phone, email, currency, logo (admin form)",
         "School.get_active() updates the singleton row",
         "Branding on every page header + every PDF footer"],
        ["Students",
         "Admission no., name, DOB, class, parent contacts, ID, photo",
         "Student row created; auto-link to Parent user via email / admission",
         "Detail page, leaderboard, parent & student portal access"],
        ["Teachers / Employees",
         "Employee no., name, role, subjects, qualifications, salary",
         "Teacher + Employee rows; admin mints teacher login",
         "Teacher list, payroll source, HR headcount KPI"],
        ["Classes · Subjects · Years",
         "Class name + grade level, subject name + code, year start/end",
         "M2M wiring Teacher↔Subject↔Class↔AcademicYear",
         "Form selects across attendance, grades, report cards"],
    ], st))

    # --- 4. Operational flows ---
    story.append(PageBreak())
    story.append(Paragraph("4 · Operational Flows", st["h1"]))

    story.append(Paragraph("4.1 · Attendance (Teacher action)", st["h2"]))
    story.append(_diagram(
        " Teacher portal → Mark Attendance\n"
        "        │\n"
        "        ▼  pick class + date, toggle Present/Absent/Late per student\n"
        "        │\n"
        " POST /api/teacher/attendance/save/\n"
        "        │\n"
        "  ┌─────┴──────┐\n"
        "  ▼            ▼\n"
        " Attendance   EmployeeAttendance  (auto check-in for THE teacher)\n"
        "  rows         row created with check_in_time = now\n"
        "        │\n"
        "        ▼  visible to Admin · HR · Student · Parent\n",
        st))

    story.append(Paragraph("4.2 · Grades & Report Card", st["h2"]))
    story.append(_diagram(
        " Teacher enters scores per subject per semester\n"
        "        │\n"
        "        ▼  Grade.percentage + letter computed on save\n"
        "        │\n"
        " build_report_card(student, grades, school, year, attendance)\n"
        "        │\n"
        "        ▼  ReportCard.pdf (branded header + footer)\n"
        "        │\n"
        "        ▼  Student & Parent portals download\n",
        st))

    story.append(Paragraph("4.3 · Fee Invoice → Payment → Income (with online flow)", st["h2"]))
    story.append(_diagram(
        " Admin / Accountant creates FeeInvoice\n"
        "        │\n"
        "        ├── (a) Office: POST /api/payments/ → FeePayment + Income\n"
        "        │\n"
        "        └── (b) Parent portal:\n"
        "                 POST /api/parent/invoice/<id>/pay/  (card or crypto)\n"
        "                          │  creates PaymentTransaction (initiated)\n"
        "                          ▼\n"
        "                 Stripe Checkout session  →  user pays on Stripe\n"
        "                          │\n"
        "                          ▼  webhook + status polling\n"
        "                 _settle_invoice() — idempotent:\n"
        "                          · FeePayment (reference = stripe session_id)\n"
        "                          · Income row\n"
        "                          · invoice status = paid / partial\n"
        "                          ▼\n"
        "                 Receipt PDF at /api/payments/<id>/receipt.pdf\n",
        st))

    story.append(Paragraph("4.4 · Salary / Payroll", st["h2"]))
    story.append(_diagram(
        " HR creates SalaryPayment (status=pending)\n"
        "        │\n"
        "        ▼  'Mark Paid' → status=paid + paid_date\n"
        "        │\n"
        "        ├── auto-creates Expense ledger row\n"
        "        ▼\n"
        " Payslip PDF at /api/salaries/<id>/payslip/  (branded)\n",
        st))

    story.append(Paragraph("4.5 · Donations · Recruitment · Inventory", st["h2"]))
    story.append(_ipo_table([
        ["Flow", "Input", "Process", "Output"],
        ["Donations", "Donor + amount + date",
         "Auto-mirrors into Income (source=donation)",
         "Donor lifetime total, Finance Report"],
        ["Recruitment", "JobPosting + Candidate stage",
         "Funnel: applied → screened → interview → hired/rejected",
         "HR funnel chart + open-roles KPI"],
        ["Inventory", "Item, qty, unit_cost, min_qty",
         "is_low_stock when qty ≤ min · total_value = qty × unit_cost",
         "HR dashboard low-stock list + assignments"],
        ["Teaching Docs", "Admin uploads PDF tagged by Subject (M2M)",
         "Empty M2M = visible to all teachers",
         "Teachers see only docs for their subjects"],
    ], st))

    # --- 5. Reporting ---
    story.append(PageBreak())
    story.append(Paragraph("5 · Reporting Layer", st["h1"]))
    story.append(Paragraph("5.1 · Finance Report (/api/reports/finance/)", st["h2"]))
    story.append(_ipo_table([
        ["Helper", "Process", "Output"],
        ["_finance_ytd_totals",
         "YTD sums for income, expense, donation, salary, outstanding",
         "5 KPI cards + Net surplus/deficit"],
        ["_finance_monthly_trend",
         "12-month buckets per stream",
         "Triple-line Chart.js trend"],
        ["_finance_breakdowns",
         "Group-by category (Expense) and source (Income)",
         "Two doughnut charts"],
    ], st, widths=(45 * mm, 75 * mm, 60 * mm)))

    story.append(Paragraph("5.2 · HR Dashboard (/api/hr/)", st["h2"]))
    story.append(Paragraph(
        "Seven focused helpers — <b>workforce</b>, <b>payroll</b>, <b>recruitment</b>, "
        "<b>training</b>, <b>performance</b>, <b>today-attendance</b>, <b>inventory</b> — "
        "each returns a partial context dict that the view merges. Output: a single "
        "dashboard with 18 KPIs + recruitment funnel + low-stock list.", st["body"]))

    story.append(Paragraph("5.3 · Academic Reports", st["h2"]))
    story.append(Paragraph(
        "Per-class Report Card ZIP export, plus leaderboards: top student per class "
        "(_top_by_class) and per academic year (_top_by_year).", st["body"]))

    # --- 6. Outputs ---
    story.append(Paragraph("6 · Generated Artefacts", st["h1"]))
    story.append(_ipo_table([
        ["Artefact", "Endpoint", "Built by", "Branded"],
        ["Report Card", "/api/students/<id>/report-card/", "erp/report_card.py", "Yes"],
        ["Invoice PDF", "/api/invoices/<id>/pdf/", "erp/invoice_pdf.py", "Yes"],
        ["Payment Receipt", "/api/payments/<id>/receipt.pdf", "erp/invoice_pdf.py", "Yes"],
        ["Payslip", "/api/salaries/<id>/payslip/", "erp/payslip_pdf.py", "Yes"],
        ["System Design (this doc)", "/api/system-design/pdf/", "erp/system_design_pdf.py", "Yes"],
    ], st))

    # --- 7. Data model ---
    story.append(PageBreak())
    story.append(Paragraph("7 · Data Model — Key Relationships", st["h1"]))
    story.append(_diagram(
        " User ─┬─ role: admin / principal / accountant / hr / teacher / parent / student\n"
        "       │\n"
        "       ├─ Teacher (1:1) ── Subject (M:N) ── Class (M:N) ── AcademicYear\n"
        "       │      ├─ SalaryPayment (1:N)\n"
        "       │      ├─ EmployeeAttendance (1:N)\n"
        "       │      └─ TeachingDocument (1:N)\n"
        "       │\n"
        "       ├─ Student (1:1) ── Class ───────────────────────────┐\n"
        "       │      ├─ Attendance (1:N)                            │\n"
        "       │      ├─ Grade (1:N) ── Subject + AcademicYear ─────┘\n"
        "       │      ├─ FeeInvoice (1:N) ── FeePayment ── PaymentTransaction\n"
        "       │      └─ CreditNote (1:N)\n"
        "       │\n"
        "       ├─ Parent (M:N Students)\n"
        "       │\n"
        "       └─ Employee ── JobPosting / Candidate / TrainingEnrollment /\n"
        "                       PerformanceReview / LeaveRequest / InventoryAssignment\n"
        "\n"
        " School (singleton) ── currency · logo · address · phone · email · motto\n"
        " Income / Expense / Donation — ledgers fed by Fee · Salary · Donation flows\n",
        st))

    # --- 8. Demo script ---
    story.append(Paragraph("8 · End-to-End Demo Script", st["h1"]))
    steps = [
        "Login as <b>Admin</b> → Dashboard (10 KPIs, recent activity).",
        "Open a Student → profile, grades, invoices, <b>Download Report Card</b>.",
        "Finance Report → 12-month trend, doughnut breakdowns, YTD net.",
        "HR Dashboard → headcount, payroll, recruitment funnel, low-stock list.",
        "Login as <b>Teacher</b> (t-004 / teacher123) → 3 actions only: attendance, grades, evaluations.",
        "Mark Attendance for a class → return to Admin → teacher's own HR check-in auto-created.",
        "Login as <b>Parent</b> (parent / password123) → see invoices → click <b>Pay</b> "
        "(test card 4242 4242 4242 4242).",
        "Login as <b>Student</b> (adm-1003 / student123) → read-only grades & invoices.",
        "Back to Admin → Salaries → <b>Mark Paid</b> → download branded Payslip PDF.",
    ]
    rows = [["#", "Step"]]
    for i, s in enumerate(steps, 1):
        rows.append([str(i), s])
    tbl = Table([[Paragraph(c, st["th" if r == 0 else "td"]) for c in row]
                 for r, row in enumerate(rows)],
                colWidths=[10 * mm, 170 * mm], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
        ("BOX", (0, 0), (-1, -1), 0.4, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(tbl)

    # --- 9. Mocked vs Live ---
    story.append(Paragraph("9 · Live vs MOCKED today", st["h1"]))
    live_rows = [
        ["Area", "Status", "Action to go live"],
        ["Stripe — Card", "LIVE (test keys)", "Swap test keys for production Stripe keys"],
        ["Stripe — Crypto", "LIVE", "Enable Crypto in Stripe Dashboard"],
        ["SendGrid email receipts", "MOCKED",
         "Set SENDGRID_API_KEY + SENDGRID_FROM_EMAIL in env — no code change"],
        ["File uploads (/media)", "Local disk",
         "Move to S3 / Cloudinary via Django storages"],
        ["Database", "SQLite", "Migrate to PostgreSQL for production"],
    ]
    data = [[Paragraph(c, st["th"]) for c in live_rows[0]]]
    for r in live_rows[1:]:
        color = GREEN if r[1].startswith("LIVE") else AMBER
        status_para = Paragraph(f"<b>{r[1]}</b>", ParagraphStyle(
            "s", parent=st["td"], textColor=color, fontName="Helvetica-Bold"))
        data.append([Paragraph(r[0], st["td"]), status_para, Paragraph(r[2], st["td"])])
    live_tbl = Table(data, colWidths=[50 * mm, 40 * mm, 90 * mm], repeatRows=1)
    live_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
        ("BOX", (0, 0), (-1, -1), 0.4, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(live_tbl)

    # --- 10. Credentials ---
    story.append(Spacer(1, 10))
    story.append(Paragraph("10 · Demo Credentials", st["h1"]))
    cred_rows = [
        ["Role", "Username", "Password"],
        ["Admin (superuser)", "admin", "admin123"],
        ["Parent (Lucas + Sofia)", "parent", "password123"],
        ["Teacher (Carlos Mendes)", "t-004", "teacher123"],
        ["Student (Miguel Costa)", "adm-1003", "student123"],
        ["Accountant", "accountant", "password123"],
        ["HR Manager", "hr", "password123"],
        ["Principal", "principal", "password123"],
    ]
    cred_data = [[Paragraph(c, st["th"]) for c in cred_rows[0]]]
    for r in cred_rows[1:]:
        cred_data.append([Paragraph(c, st["td"]) for c in r])
    cred_tbl = Table(cred_data, colWidths=[70 * mm, 55 * mm, 55 * mm], repeatRows=1)
    cred_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
        ("BOX", (0, 0), (-1, -1), 0.4, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(cred_tbl)
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Stripe test card: <b>4242 4242 4242 4242</b> · any future expiry · any CVC.",
        st["muted"]))

    doc.build(story, onFirstPage=make_footer_callback(school),
              onLaterPages=make_footer_callback(school))
    return buf.getvalue()
