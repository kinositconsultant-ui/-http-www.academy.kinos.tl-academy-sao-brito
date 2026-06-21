# PRD — Instituto São João de Brito · Academy & Finance ERP

## Original Problem Statement
> "Can we build with Django and Python? I want enterprise academy and finance system.
> Yes, add more finance school registration, teacher salary, expense, donor support
> even and including human resource management for academy."
> User then asked: "Add the school name **Instituto São João de Brito**."

## Architecture
- **Stack:** Django 5.0.6 + Django Templates + Tailwind (CDN) + SQLite + Whitenoise.
- **Entrypoint:** `/app/backend/server.py` exposes `app = get_asgi_application()`.
  Supervisor runs `uvicorn server:app --host 0.0.0.0 --port 8001`.
- **All routes prefixed with `/api/`** because the platform ingress only forwards
  `/api/*` to port 8001. The React frontend on port 3000 serves a static
  `index.html` that redirects to `/api/dashboard/`.
- **Apps:** `accounts` (User w/ roles, School), `erp` (everything else).
- **Auth:** Django's built-in session auth; custom `User` extends `AbstractUser` with
  `role` choices: Admin / Principal / Teacher / Accountant / HR / Staff.

## User Personas
- **Administrator** — full access including Django Admin and System Users.
- **Principal** — school operations.
- **Accountant** — fees, salaries, expenses, donors, donations, reports.
- **HR Manager** — employees, leave requests.
- **Teacher / Staff** — read-mostly operational use.

## Core Requirements (static)
1. School registration (single-tenant profile, editable).
2. Students, Teachers, Classes, Subjects management.
3. Attendance & Grades recording.
4. Fee Structures, Fee Invoices, Fee Payments (auto-mirrored into Income ledger).
5. Teacher Salary tracking (Mark Paid auto-creates an Expense).
6. Expenses & Income ledgers.
7. Donor support: Donor CRUD + Donations (auto-mirrored into Income ledger).
8. HR: Employees, Leave Requests with approve/reject.
9. Finance Report (YTD income, expense, net, donations, breakdowns by category/source).

## Implemented (2026-02)
- Production hardening (2026-02-20):
  - **Tailwind built locally** via the standalone CLI — `static/css/app.css`
    (~22 KB minified) replaces the 3 MB CDN runtime in `base.html`.
    `STATICFILES_DIRS = [BASE_DIR/"static"]` lets `collectstatic` pick it up
    and Whitenoise serves it with manifest hashing & gzip. A
    `python manage.py build_tailwind` command rebuilds on demand
    (use `--watch` during template work).
  - **SendGrid live path** wired through the official `sendgrid` SDK
    (`erp/mail.py`). When both `SENDGRID_API_KEY` and `SENDGRID_FROM_EMAIL`
    are set the SDK is used; otherwise the existing MOCK path keeps writing
    to the SentEmail audit log + stdout — no code flip needed to go live.
  - **Per-invoice PDF** (`erp/invoice_pdf.py`) — two new endpoints:
    - `GET /api/invoices/<id>/pdf/` — full invoice PDF (header, billed-to,
      meta, line item, totals with paid-to-date & balance due, payment
      history). Button on invoice detail; also accessible from the student
      portal invoice list.
    - `GET /api/payments/<id>/receipt.pdf` — payment receipt PDF (big
      "amount received" banner, method, reference, balance after). Link on
      each payment row.
    Access enforced for admin / accountant / principal / linked parent /
    student-self.
- Student self-service portal (2026-02-20)
- Dashboard Chart.js layout fix (2026-02-20)
- Bulk PDF report cards verified end-to-end (2026-02-20)
- **Institutional PDF branding (2026-02-22)** — Centralized `erp/pdf_brand.py`
  injects school logo + name + motto into the header and address + phone +
  email + page number into the footer of every generated PDF (Report Card,
  Invoice, Payment Receipt, Payslip). Validated by extracting text from
  generated PDFs — header/footer strings present on all three.

## Implemented (2026-01)
- Code-review pass (2026-01-20):
  - Removed dead mis-located management command at `accounts/management/__init__.py`
    (it was never executed by Django — should have been `commands/<name>.py`).
  - Refactored `erp/views.py` `dashboard()` 17 locals → 1 helper + 3 focused
    builders (`_count_kpis`, `_money_kpis`, `_recent_activity`).
  - Refactored `_save_form()` 8 args → `FormView` dataclass + 2 args; updated
    all 30 callers automatically.
  - Cleaned style issues in `scripts/seed.py`. Lint: **0 errors**.
  - React frontend hook warnings (`App.js`, `use-toast.js`) are in the
    pre-existing CRA scaffold which is no longer used — the frontend is now a
    static redirect (`public/index.html` → `/api/dashboard/`); React never
    mounts. Files left untouched to avoid disturbing the unused frontend
    service.
- Login / Logout / Session auth with role-based User model. ✅
- School profile seeded with **Instituto São João de Brito** (EUR currency, motto
  "Scientia · Caritas · Veritas"). ✅
- Dashboard with 10 KPIs + Quick Actions + Recent Activity (payments / expenses /
  donations). ✅
- Students CRUD + search + detail page with invoices & grades. ✅
- Teachers CRUD with monthly salary & subject ManyToMany. ✅
- Classes, Subjects, Academic Years CRUD. ✅
- Attendance CRUD, Grades CRUD with auto % and letter grade. ✅
- Fee Structures CRUD. ✅
- Fee Invoices CRUD with filters (pending/partial/paid/overdue), Invoice detail
  with embedded Payment form that auto-creates Income entry on success. ✅
- Teacher Salaries CRUD; "Mark Paid" auto-creates Expense entry. ✅
- Expenses + Incomes CRUD with totals. ✅
- Donors CRUD + Donor detail page with lifetime total. Donations CRUD that
  auto-creates Income entry. ✅
- HR Employees CRUD + Leave Requests CRUD with approve/reject inline actions. ✅
- Finance Report (/api/reports/finance/) YTD with category & source breakdowns. ✅
- System Users management (admin-only). ✅
- Django Admin enabled at /api/admin/. ✅
- Seed script: admin/admin123 + accountant/hr/principal accounts, sample data. ✅
- Verified end-to-end by testing agent (iteration_2.json — 100% pass). ✅

## P0 / P1 Backlog
- **P1** — Built Tailwind asset instead of CDN script (production audit warning).
- **P1** — PDF invoice & receipt download.
- **P1** — Bulk attendance marking (one form per class per date).
- **P1** — Email invoice / payment receipt to parents (needs SendGrid / SMTP).
- **P2** — Parent portal (read-only view of own child's fees & grades).
- **P2** — Online payment gateway (Stripe / Razorpay) — collect fees online.
- **P2** — Report cards (PDF) per term.
- **P2** — Bank reconciliation / multi-account ledger.
- **P2** — Multi-tenant / multi-campus support.
- **P2** — i18n (Portuguese UI strings) — useful given the school's Lisbon context.

## Test Credentials
See `/app/memory/test_credentials.md`.

## Next Actions
1. Add PDF receipt download for invoice payments.
2. Bulk class attendance entry.
3. Email notifications via SendGrid integration.
