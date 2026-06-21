# Instituto São João de Brito — Academy & Finance ERP
## System Design · Flow · Input → Process → Output

---

## 1. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         WEB BROWSER (User)                       │
│       Admin · Principal · Accountant · HR · Teacher · Parent     │
│                            · Student                             │
└──────────────────────────┬───────────────────────────────────────┘
                           │ HTTPS (sessions + CSRF)
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  Kubernetes Ingress  → /api/*  → Django (uvicorn :8001)          │
│                        /*      → static redirect (React bypass)  │
└──────────────────────────┬───────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    DJANGO 5.0.6  (server-rendered)               │
│  ┌────────────┐ ┌─────────┐ ┌────────┐ ┌────────┐ ┌──────────┐   │
│  │ accounts   │ │  erp    │ │ portal │ │teacher │ │   hr     │   │
│  │ (Users,    │ │ (core   │ │ (parent│ │_views  │ │ _views   │   │
│  │  School)   │ │ models) │ │+studen)│ │        │ │          │   │
│  └────────────┘ └─────────┘ └────────┘ └────────┘ └──────────┘   │
└────┬──────────────────┬──────────────────┬───────────────────────┘
     ▼                  ▼                  ▼
┌─────────┐      ┌────────────┐      ┌──────────────┐
│ SQLite  │      │  /media    │      │  3rd-party   │
│ (data)  │      │ (uploads)  │      │  Stripe /    │
│         │      │            │      │  SendGrid    │
└─────────┘      └────────────┘      └──────────────┘
```

**Stack:** Django · Django Templates · Tailwind (locally built) · Chart.js · ReportLab (PDF) · `emergentintegrations` (Stripe) · SendGrid SDK (mocked until key provided).

---

## 2. Authentication & Role Routing

```
┌──────────┐    POST /api/login/    ┌──────────────────────┐
│  Login   │ ───────────────────► │ Django session auth +  │
│  page    │                      │ CSRF middleware        │
└──────────┘                      └──────────┬─────────────┘
                                             │ role lookup
        ┌────────────────────────────────────┼───────────────────┐
        ▼          ▼          ▼          ▼   ▼          ▼        ▼
   Administrator Principal Accountant  HR  Teacher  Parent    Student
        │          │          │        │      │        │         │
        ▼          ▼          ▼        ▼      ▼        ▼         ▼
   /api/        same as    /api/      /api/  /api/   /api/    /api/
   dashboard/   admin      reports/   hr/    teacher parent   student
                           finance/          /       /        /
```

Roles are stored on `accounts.User.role`; the decorator `@_hr_required` (etc.) guards each scope.

---

## 3. Core Domain Modules — IPO Tables

### 3.1 School Profile (single-tenant)

| INPUT (UI form / seed) | PROCESS | OUTPUT |
|---|---|---|
| Name, motto, address, phone, email, currency, logo | `School.get_active()` updates the singleton row | Branding visible on every page header + every PDF footer |

### 3.2 Students

| INPUT | PROCESS | OUTPUT |
|---|---|---|
| Admission no., name, DOB, class, parent contacts, ID type/no., address, photo | `Student` row created; auto-linked to Parent user via email/admission match | Student detail page, leaderboard, parent & student portal access |

### 3.3 Teachers / Employees

| INPUT | PROCESS | OUTPUT |
|---|---|---|
| Employee no., name, role, subjects, qualifications, monthly salary, hire date | `Teacher` + `Employee` rows; admin can "Create login" to mint a teacher account | Teacher list, payroll source, HR dashboard headcount |

### 3.4 Classes · Subjects · Academic Years

| INPUT | PROCESS | OUTPUT |
|---|---|---|
| Class name + grade level, subject name + code, year start/end | M2M wiring between Teacher↔Subject↔Class↔AcademicYear | Form selects across attendance, grades, report cards |

---

## 4. Operational Flows

### 4.1 Attendance (class-day) — Teacher Action

```
Teacher portal ─▶ "Mark Attendance" page
                      │
                      ▼
            Picks class + date  ──▶  Toggles Present/Absent/Late per student
                      │
                      ▼
              POST /api/teacher/attendance/save/
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
  Attendance rows           EmployeeAttendance row
  created/updated           auto-created for THE TEACHER
                            (check-in = now)
                      │
                      ▼
            Visible to Admin · HR · Student · Parent portals
```

### 4.2 Grades & Report Card

```
Teacher enters scores (per subject · per semester)
        │
        ▼
   Grade.percentage + letter auto-computed on save
        │
        ▼
   Bulk Report Card export:
   build_report_card(student, grades, school, year, attendance) ──▶ ReportCard.pdf
        │                                                              │
        ▼                                                              ▼
   Includes: branded header · student block · per-semester grade table │
            · summary KPIs · signatures · branded footer (addr/phone)  │
                                                                       ▼
                                                       Student & Parent download
```

### 4.3 Fee Invoice → Payment → Income Ledger (with online payment)

```
Admin/Accountant creates  FeeInvoice
        │
        ├── (a) Office payment ──▶ POST /api/payments/  → FeePayment + Income row
        │                                                 (auto-mirrored)
        │
        └── (b) Online (Parent portal)
                 │
                 ▼
            POST /api/parent/invoice/{id}/pay/  (card or crypto)
                 │   creates PaymentTransaction (status=initiated)
                 ▼
            Stripe Checkout session → user pays on Stripe
                 │
                 ▼
            Webhook + /api/parent/invoice/{id}/status/ polling
                 │
                 ▼
            _settle_invoice() — idempotent:
              · creates FeePayment (reference = stripe session_id)
              · creates Income row
              · marks invoice paid / partial
                 │
                 ▼
            Receipt PDF available at /api/payments/{id}/receipt.pdf
```

### 4.4 Salary / Payroll

```
HR creates SalaryPayment (status=pending)
        │
        ▼
"Mark Paid"  ──▶  status=paid, paid_date=today
        │           │
        │           ├── auto-creates Expense ledger row
        │           ▼
        ▼      Payslip PDF available at /api/salaries/{id}/payslip/
   HR dashboard:                  (branded header + footer)
   paid_this_month aggregates
```

### 4.5 Donations

```
Donor CRUD ──▶ Donation (amount, date, source)
                  │
                  ▼
            auto-mirrors into Income (source=donation)
                  │
                  ▼
            Donor detail = lifetime total · Finance Report includes donations
```

### 4.6 HR — Recruitment · Training · Performance

```
JobPosting ──▶ Candidate (stage funnel: applied→screened→interview→hired/rejected)
                                            │
TrainingProgram ──▶ TrainingEnrollment      ▼
                                       PerformanceReview (rating + period)
                                            │
                            HR dashboard aggregates all of the above
```

### 4.7 Inventory

```
InventoryCategory ──▶ InventoryItem (qty, unit_cost, min_qty)
                            │
                            ├── is_low_stock when qty ≤ min_qty
                            ├── total_value = qty × unit_cost
                            ▼
                        InventoryAssignment (item → employee, status)
                            │
                            ▼
                  HR dashboard surfaces low_stock + assignments
```

### 4.8 Teaching Documents

```
Admin uploads PDF (syllabus / lesson plan)
        │
        ▼
TeachingDocument row + file in /media/teaching/
        │
        ├── Tagged by Subject (M2M) — empty M2M means "all teachers"
        │
        ▼
Teachers see only the docs tagged to subjects they teach (or "all teachers")
```

---

## 5. Reporting

### 5.1 Finance Report (`/api/reports/finance/`)

| INPUT | PROCESS (refactored 2026-02) | OUTPUT |
|---|---|---|
| Today's date + active School | `_finance_ytd_totals` → YTD sums for income, expense, donation, salary, outstanding | KPI cards |
| (same) | `_finance_monthly_trend` → 12-month buckets per stream | Chart.js triple line chart |
| (same) | `_finance_breakdowns` → group-by category / source | Two doughnut charts |

### 5.2 HR Dashboard (`/api/hr/`)

7 section helpers — workforce · payroll · recruitment · training · performance · today-attendance · inventory — each returns a partial context dict that the view merges. Output: a single dashboard with 18 KPIs + funnel chart + low-stock list.

### 5.3 Academic Reports

Per-class report card bulk download (ZIP of PDFs) + leaderboard top-by-class and top-by-year (`_top_by_class()`, `_top_by_year()`).

---

## 6. Generated Artefacts (Outputs)

| Artefact | Endpoint | Built by | Branding |
|---|---|---|---|
| Report Card | `/api/students/{id}/report-card/` | `erp/report_card.py` | logo + footer ✓ |
| Invoice PDF | `/api/invoices/{id}/pdf/` | `erp/invoice_pdf.py` | logo + footer ✓ |
| Payment Receipt | `/api/payments/{id}/receipt.pdf` | `erp/invoice_pdf.py` | logo + footer ✓ |
| Payslip PDF | `/api/salaries/{id}/payslip/` | `erp/payslip_pdf.py` | logo + footer ✓ |
| Stripe Receipt (live) | Stripe-hosted | Stripe | n/a |
| SentEmail audit log | DB table | `erp/mail.py` | mocked until key wired |

All branded PDFs share the same header (logo · school name · motto · doc-type · doc-id) and footer (address · phone · email · page number) via `erp/pdf_brand.py`.

---

## 7. Data Model — Key Relationships

```
User ─┬─ role: admin/principal/accountant/hr/teacher/parent/student
      │
      ├─ Teacher  (1:1) ─── Subject (M:N) ─── Class (M:N) ─── AcademicYear
      │     │                                       │
      │     ├─ SalaryPayment (1:N)                  │
      │     ├─ EmployeeAttendance (1:N)             │
      │     └─ TeachingDocument (1:N)               │
      │                                             │
      ├─ Student (1:1) ──── Class ─────────────────┘
      │     │
      │     ├─ Attendance (1:N)
      │     ├─ Grade (1:N) ── Subject + AcademicYear
      │     ├─ FeeInvoice (1:N) ── FeePayment (1:N) ── PaymentTransaction
      │     └─ CreditNote (1:N)
      │
      ├─ Parent  (M:N Students)
      │
      └─ Employee ─── JobPosting / Candidate / TrainingEnrollment /
                      PerformanceReview / LeaveRequest / InventoryAssignment

School (singleton) ── currency · logo · address · phone · email · motto
Income / Expense / Donation — ledgers fed by Fee/Salary/Donation flows
```

---

## 8. End-to-End Demo Script (suggested for the live walkthrough)

1. **Login as Admin** → land on Dashboard (10 KPIs, recent activity).
2. **Open a Student** → show profile, grades, invoices, "Download Report Card".
3. **Open Finance Report** → highlight 12-month trend, doughnut breakdowns, YTD net.
4. **Open HR Dashboard** → headcount, payroll, recruitment funnel, low-stock list.
5. **Log out · Login as Teacher** (`t-004 / teacher123`) → restricted to 3 actions: attendance, grades, evaluations.
6. **Mark Attendance** for a class → return to admin → show the teacher's own HR check-in was auto-created.
7. **Log out · Login as Parent** (`parent / password123`) → see child's invoices → click "Pay" (Stripe test card `4242 4242 4242 4242`).
8. **Log out · Login as Student** (`adm-1003 / student123`) → read-only view of grades & invoices.
9. **Back to Admin · Salaries** → "Mark Paid" on a pending row → download Payslip PDF (branded).

---

## 9. What's MOCKED vs LIVE Today

| Area | Status |
|---|---|
| Stripe Card payments | **LIVE** (`emergentintegrations` + Stripe test keys) |
| Stripe Crypto payments | **LIVE** (must be enabled in Stripe Dashboard) |
| SendGrid email receipts | **MOCKED** — writes to `SentEmail` audit log + stdout. Set `SENDGRID_API_KEY` + `SENDGRID_FROM_EMAIL` to go live (no code change). |
| File uploads (`/media`) | **LOCAL DISK** — production should move to S3/Cloudinary. |
| Database | **SQLite** — production should migrate to PostgreSQL. |

---

## 10. Test Credentials (for the demo)

```
admin    / admin123      → full access (Django admin too)
parent   / password123   → children: Lucas Oliveira, Sofia Rodrigues
t-004    / teacher123    → Carlos Mendes (History)
adm-1003 / student123    → Miguel Costa (top of leaderboard)
accountant / password123
hr         / password123
principal  / password123
```

Stripe test card: `4242 4242 4242 4242` · any future expiry · any CVC.

---

_Last updated: 2026-02-22 — see `/app/memory/PRD.md` for the changelog._
