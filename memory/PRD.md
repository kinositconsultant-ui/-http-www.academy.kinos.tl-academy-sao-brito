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
- Dashboard Chart.js layout fix (2026-02-20): all three canvases wrapped in
  fixed-height `.relative` containers (220/220/340px) with
  `maintainAspectRatio: false` — chart bars now render at the correct size
  instead of expanding off-screen. Stale in-memory templates were the actual
  blocker; a backend restart cleared the cached compiled templates.
- Bulk PDF report cards verified end-to-end (2026-02-20):
  `GET /api/classes/<id>/report-cards.zip[?year=<id>]` returns a valid ZIP
  containing one `report-card_<name>_<admission>.pdf` per active student.
  Trigger button is on the Academic Report page.

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
