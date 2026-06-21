"""Regression tests after refactor of finance_report (views.py) and
hr_dashboard (hr_views.py). Helpers were extracted but behavior must be
identical: same KPIs, same chart context keys, same currency, no 500s.

Also re-verifies: login flow (CSRF + Referer + session), PDF endpoints
(payslip, invoice, report card) return application/pdf, portal_views.py
endpoints reachable.
"""
import os
import re
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
LOGIN_URL = f"{BASE_URL}/api/login/"


# ---------- helpers / fixtures ----------

def _csrf(html: str) -> str:
    m = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]+)"', html)
    assert m, "csrf token not found in login form"
    return m.group(1)


def _login(session: requests.Session, username: str, password: str) -> requests.Response:
    g = session.get(LOGIN_URL)
    assert g.status_code == 200, f"GET login failed: {g.status_code}"
    token = _csrf(g.text)
    headers = {"Referer": LOGIN_URL}
    r = session.post(
        LOGIN_URL,
        data={
            "csrfmiddlewaretoken": token,
            "username": username,
            "password": password,
        },
        headers=headers,
        allow_redirects=False,
    )
    return r


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = _login(s, "admin", "admin123")
    assert r.status_code in (301, 302), (
        f"admin login expected redirect, got {r.status_code}: {r.text[:300]}")
    # follow once to confirm dashboard
    dash = s.get(f"{BASE_URL}/api/dashboard/")
    assert dash.status_code == 200, f"dashboard not reachable: {dash.status_code}"
    return s


@pytest.fixture(scope="module")
def parent_session():
    s = requests.Session()
    r = _login(s, "parent", "password123")
    assert r.status_code in (301, 302), f"parent login failed: {r.status_code}"
    return s


# ---------- 1. Login + dashboard ----------

class TestLogin:
    def test_admin_login_redirects_to_dashboard(self):
        s = requests.Session()
        r = _login(s, "admin", "admin123")
        assert r.status_code in (301, 302)
        # Location header should point at dashboard (allow trailing redirects)
        loc = r.headers.get("Location", "")
        assert "/api/dashboard" in loc or "/dashboard" in loc or loc.endswith("/"), (
            f"unexpected redirect location: {loc!r}")

    def test_admin_dashboard_loads(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/dashboard/")
        assert r.status_code == 200
        # sanity: page actually rendered (not just a redirect loop)
        assert "<html" in r.text.lower()


# ---------- 2. Finance report (refactored finance_report) ----------

class TestFinanceReport:
    def test_finance_report_status(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/reports/finance/")
        assert r.status_code == 200, f"finance report returned {r.status_code}"

    def test_finance_report_contains_kpi_sections(self, admin_session):
        """The refactored helpers must still populate the same template
        sections: YTD totals, net, monthly trend (3 series), and the
        category/source doughnut breakdowns."""
        r = admin_session.get(f"{BASE_URL}/api/reports/finance/")
        assert r.status_code == 200
        html = r.text.lower()

        # YTD KPI labels (template uses pluralised "Salaries")
        for needle in ["income", "expense", "donation", "salar", "outstanding"]:
            assert needle in html, f"missing KPI label: {needle}"

        # net surplus / deficit text (template just labels it "Net")
        assert ">net<" in html or "net</" in html or "uppercase tracking-widest" in html, (
            "net surplus/deficit section not rendered")

        # Trend chart series → context provides trend_labels/trend_income/...
        # Look for the JSON arrays embedded in the page (Chart.js init).
        assert "trend" in html or "monthly" in html, "monthly trend section missing"

        # Doughnut breakdowns
        assert "by category" in html or "expense by category" in html or "category" in html
        assert "by source" in html or "income by source" in html or "source" in html

    def test_finance_report_chart_payloads_present(self, admin_session):
        """Make sure the chart JSON payload arrays (cat_chart / src_chart /
        trend_*) appear in the rendered template — these come straight from
        the extracted helpers."""
        r = admin_session.get(f"{BASE_URL}/api/reports/finance/")
        text = r.text
        # cat_chart / src_chart / trend arrays are usually JSON-encoded into <script>
        # The template renders them via |safe / json_script — check at least one
        # numeric data array is present.
        has_chart_data = bool(re.search(r"\[\s*[\d\.\,\s]+\s*\]", text))
        assert has_chart_data, "no chart data arrays detected in finance report"

    def test_finance_report_currency_code(self, admin_session):
        """currency_code from active School should appear (USD/EUR/etc.)."""
        r = admin_session.get(f"{BASE_URL}/api/reports/finance/")
        # iteration_2 baseline shows EUR amounts; accept any 3-letter code in template.
        assert re.search(r"\b(USD|EUR|GBP|BRL|INR|JPY|CAD|AUD)\b", r.text), (
            "no currency code rendered on finance report")


# ---------- 3. HR dashboard (refactored hr_dashboard) ----------

class TestHRDashboard:
    def test_hr_dashboard_status(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/hr/")
        assert r.status_code == 200, f"hr dashboard returned {r.status_code}"

    def test_hr_dashboard_sections(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/hr/")
        html = r.text.lower()
        # The 7 sections rebuilt by helpers
        for section in [
            "workforce", "payroll", "recruitment",
            "training", "performance", "attendance", "inventory",
        ]:
            assert section in html, f"hr dashboard missing section: {section}"

    def test_hr_dashboard_workforce_keys(self, admin_session):
        """The helpers expose: active, inactive, on_leave_today, total_employees,
        paid_this_month, pending_payslips, open_jobs, candidates_in_pipeline,
        funnel_chart, active_trainings, enrollments, avg_rating,
        reviews_this_quarter, today_present, today_total, today_pct,
        total_items, low_stock_count, low_stock_items, inventory_value,
        items_assigned. The template should surface most of these as labels.
        """
        r = admin_session.get(f"{BASE_URL}/api/hr/")
        html = r.text.lower()
        # Spot-check labels that almost certainly appear in any reasonable HR dash
        expected_any = [
            "active", "leave", "pending", "open jobs", "candidates",
            "training", "review", "present", "low stock", "assigned",
        ]
        missing = [k for k in expected_any if k not in html]
        # Allow at most 2 of these label strings to be missing (templates wording can vary)
        assert len(missing) <= 2, f"too many HR labels missing: {missing}"


# ---------- 4. PDF endpoints (branding fix regression) ----------

def _find_first_id(session, url, pattern):
    """Scrape a list page and return the first integer id from URLs matching pattern."""
    r = session.get(url)
    assert r.status_code == 200, f"{url} returned {r.status_code}"
    m = re.search(pattern, r.text)
    return int(m.group(1)) if m else None


class TestPDFs:
    def test_invoice_pdf(self, admin_session):
        # Discover an invoice id from the invoice list
        inv_id = _find_first_id(
            admin_session, f"{BASE_URL}/api/invoices/",
            r"/api/invoices/(\d+)/")
        assert inv_id, "no invoice id discovered from /api/invoices/"
        r = admin_session.get(f"{BASE_URL}/api/invoices/{inv_id}/pdf/")
        assert r.status_code == 200, f"invoice pdf status {r.status_code}"
        assert r.headers.get("Content-Type", "").startswith("application/pdf"), (
            f"invoice pdf content-type wrong: {r.headers.get('Content-Type')}")
        assert len(r.content) > 5000, f"invoice pdf too small: {len(r.content)} bytes"
        assert r.content[:4] == b"%PDF", "invoice pdf missing %PDF magic"

    def test_payslip_pdf(self, admin_session):
        # URL is /api/hr/payslip/<pk>.pdf - find a SalaryPayment id from /api/salaries/
        sal_id = _find_first_id(
            admin_session, f"{BASE_URL}/api/salaries/",
            r"/api/(?:salaries|hr/payslip)/(\d+)")
        if not sal_id:
            pytest.skip("no salary payment id discovered")
        r = admin_session.get(f"{BASE_URL}/api/hr/payslip/{sal_id}.pdf")
        assert r.status_code == 200, f"payslip pdf status {r.status_code}"
        assert r.headers.get("Content-Type", "").startswith("application/pdf"), (
            f"payslip content-type: {r.headers.get('Content-Type')}")
        assert len(r.content) > 5000, f"payslip too small: {len(r.content)} bytes"
        assert r.content[:4] == b"%PDF"

    def test_report_card_pdf(self, admin_session):
        # /api/students/<pk>/report-card/
        stu_id = _find_first_id(
            admin_session, f"{BASE_URL}/api/students/",
            r"/api/students/(\d+)/")
        assert stu_id, "no student id discovered from /api/students/"
        r = admin_session.get(f"{BASE_URL}/api/students/{stu_id}/report-card/")
        assert r.status_code == 200, f"report card status {r.status_code}: {r.text[:200]}"
        assert r.headers.get("Content-Type", "").startswith("application/pdf"), (
            f"report card content-type: {r.headers.get('Content-Type')}")
        assert len(r.content) > 5000, f"report card too small: {len(r.content)} bytes"
        assert r.content[:4] == b"%PDF"


# ---------- 5. Portal / Stripe defensive init regression ----------

class TestPortalDefensive:
    def test_parent_portal_loads(self, parent_session):
        r = parent_session.get(f"{BASE_URL}/api/parent/")
        assert r.status_code == 200, f"parent portal returned {r.status_code}: {r.text[:200]}"
        assert "<html" in r.text.lower()

    def test_parent_portal_no_500_on_invoice_pay_routes(self, parent_session):
        """portal_views.py invoice_pay / invoice_pay_crypto / invoice_payment_status
        got defensive `session = None` / `live = None` initializers. Just make
        sure GET routes don't 500 (they may 302/403 if no invoice is owed)."""
        # Find an invoice id visible from the parent dashboard, if any
        r = parent_session.get(f"{BASE_URL}/api/parent/")
        m = re.search(r"/api/parent/invoice/(\d+)/pay/", r.text)
        if not m:
            pytest.skip("no parent invoice pay link on dashboard")
        inv_id = m.group(1)
        for path in [
            f"/api/parent/invoice/{inv_id}/pay/",
            f"/api/parent/invoice/{inv_id}/pay-crypto/",
            f"/api/parent/invoice/{inv_id}/payment-status/",
        ]:
            resp = parent_session.get(f"{BASE_URL}{path}", allow_redirects=False)
            assert resp.status_code < 500, (
                f"{path} raised server error {resp.status_code}: {resp.text[:200]}")
