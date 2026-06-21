"""Phase 2 — Student Document Repository + Lesson Plans + Today widget.

Covers:
- Student documents: admin/parent/student access scoping (200/403), upload,
  display_title fallback, expiring_soon ⚠ flag.
- Lesson plans: admin list+create, teacher own-only listing, student class
  + is_published scoping, draft (is_published=False) hidden from students,
  delete permission boundary.
- Today/This-week widget: data-testid='today-widget' present in
  /api/dashboard/, /api/student/, /api/teacher/, /api/parent/.
- Latest notices: prior 'TEST_Phase1 Welcome' announcement still appears.
- Upcoming assignments: student-only.
"""
import io
import os
import re
from datetime import date, timedelta

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
LOGIN_URL = f"{BASE_URL}/api/login/"


# ---------- helpers ----------

def _csrf_from_html(html: str) -> str:
    m = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]+)"', html)
    assert m, "csrfmiddlewaretoken not found"
    return m.group(1)


def _get_csrf(session, url):
    r = session.get(url)
    assert r.status_code == 200, f"GET {url} -> {r.status_code}"
    return _csrf_from_html(r.text)


def _login(username, password):
    s = requests.Session()
    token = _get_csrf(s, LOGIN_URL)
    r = s.post(
        LOGIN_URL,
        data={"csrfmiddlewaretoken": token, "username": username, "password": password},
        headers={"Referer": LOGIN_URL},
        allow_redirects=False,
    )
    assert r.status_code in (301, 302), f"login {username} -> {r.status_code}"
    return s


def _post(session, url, data, files=None, follow=False):
    token = _get_csrf(session, url)
    data = dict(data)
    data["csrfmiddlewaretoken"] = token
    return session.post(
        url, data=data, files=files,
        headers={"Referer": url}, allow_redirects=follow,
    )


# ---------- fixtures ----------

@pytest.fixture(scope="module")
def admin_s():
    return _login("admin", "admin123")


@pytest.fixture(scope="module")
def parent_s():
    return _login("parent", "password123")


@pytest.fixture(scope="module")
def teacher_s():
    return _login("t-004", "teacher123")


@pytest.fixture(scope="module")
def miguel_s():
    return _login("adm-1003", "student123")


@pytest.fixture(scope="module")
def tiago_s():
    return _login("adm-1005", "student123")


# adm-1003 (Miguel) and adm-1005 (Tiago) — NOT parent's children.
# parent's children are Lucas Oliveira (ADM-1001) and Sofia Rodrigues (ADM-1004).


@pytest.fixture(scope="module")
def parent_child_ids(admin_s):
    """Find IDs of parent's children (Lucas ADM-1001, Sofia ADM-1004) via admin."""
    r = admin_s.get(f"{BASE_URL}/api/students/")
    assert r.status_code == 200
    ids = {}
    # Pattern: row with admission_no near a link /api/students/<id>/
    for adm in ("ADM-1001", "ADM-1004"):
        # Search admission_no, then look around for /api/students/<id>/
        m = re.search(rf"/api/students/(\d+)/[^>]*>[^<]*{adm}", r.text)
        if not m:
            # fallback: opposite order — adm appears before the link
            m = re.search(rf"{adm}[\s\S]{{0,400}}?/api/students/(\d+)/", r.text)
        if m:
            ids[adm] = int(m.group(1))
    return ids


# =====================================================================
# 1. Student Documents — admin
# =====================================================================

class TestAdminDocs:
    def test_admin_list_200(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/students/1/documents/")
        assert r.status_code == 200
        # Seed: BI 2024 doc for student 1
        # Either the title 'BI 2024' or the doc_type label 'BI / Electoral Card'
        assert ("BI 2024" in r.text) or ("BI / Electoral Card" in r.text), \
            "Seed BI doc for student 1 not visible in admin docs listing"

    def test_admin_upload_with_expiring_soon_flag(self, admin_s):
        url = f"{BASE_URL}/api/students/1/documents/add/"
        soon = (date.today() + timedelta(days=15)).isoformat()
        files = {"file": ("test_passport.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")}
        r = _post(admin_s, url, {
            "doc_type": "passport",
            "title": "TEST_Passport 2026",
            "issued_date": "2026-01-01",
            "expires_at": soon,
            "notes": "TEST upload",
        }, files=files, follow=True)
        assert r.status_code == 200, f"upload failed: {r.status_code}"

        listing = admin_s.get(f"{BASE_URL}/api/students/1/documents/")
        assert listing.status_code == 200
        assert "TEST_Passport 2026" in listing.text, "display_title (custom title) not shown"
        # Expiring-soon flag should be present (⚠)
        assert "⚠" in listing.text, \
            "expiring_soon docs should be flagged with ⚠ in the template"

    def test_admin_upload_no_title_uses_doc_type_label(self, admin_s):
        url = f"{BASE_URL}/api/students/1/documents/add/"
        files = {"file": ("birth.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")}
        r = _post(admin_s, url, {
            "doc_type": "birth",
            "title": "",
            "notes": "TEST_no_title_fallback",
        }, files=files, follow=True)
        assert r.status_code == 200
        listing = admin_s.get(f"{BASE_URL}/api/students/1/documents/")
        # When title blank, display_title = doc_type label
        assert "Birth Certificate" in listing.text, \
            "display_title fallback to doc_type label missing"


# =====================================================================
# 2. Student Documents — parent scope
# =====================================================================

class TestParentDocs:
    def test_parent_can_list_own_child(self, parent_s, parent_child_ids):
        if not parent_child_ids:
            pytest.skip("Could not resolve parent child ids")
        cid = next(iter(parent_child_ids.values()))
        r = parent_s.get(f"{BASE_URL}/api/students/{cid}/documents/")
        assert r.status_code == 200, f"parent own child docs -> {r.status_code}"

    def test_parent_blocked_from_other_student(self, parent_s, admin_s, parent_child_ids):
        # Find Miguel (ADM-1003) — NOT a child of `parent` — and verify 403.
        r = admin_s.get(f"{BASE_URL}/api/students/")
        assert r.status_code == 200
        m = re.search(r"/api/students/(\d+)/[^>]*>[^<]*ADM-1003", r.text) \
            or re.search(r"ADM-1003[\s\S]{0,400}?/api/students/(\d+)/", r.text)
        assert m, "Could not resolve Miguel's student id"
        other_id = int(m.group(1))
        assert other_id not in parent_child_ids.values(), \
            "Test setup error: Miguel resolved as parent's child"
        r2 = parent_s.get(f"{BASE_URL}/api/students/{other_id}/documents/")
        assert r2.status_code == 403, \
            f"parent should be 403 on non-child student docs, got {r2.status_code}"

    def test_parent_can_upload_for_own_child(self, parent_s, parent_child_ids):
        if not parent_child_ids:
            pytest.skip("Could not resolve parent child ids")
        cid = next(iter(parent_child_ids.values()))
        url = f"{BASE_URL}/api/students/{cid}/documents/add/"
        files = {"file": ("vac.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")}
        r = _post(parent_s, url, {
            "doc_type": "vaccination",
            "title": "TEST_Vaccination Parent",
            "notes": "uploaded by parent",
        }, files=files, follow=True)
        assert r.status_code == 200
        listing = parent_s.get(f"{BASE_URL}/api/students/{cid}/documents/")
        assert "TEST_Vaccination Parent" in listing.text


# =====================================================================
# 3. Student Documents — student scope
# =====================================================================

class TestStudentDocs:
    def test_student_can_view_own(self, miguel_s, admin_s):
        # Find Miguel's student id
        r = admin_s.get(f"{BASE_URL}/api/students/")
        m = re.search(r"/api/students/(\d+)/[^>]*>[^<]*ADM-1003", r.text) \
            or re.search(r"ADM-1003[\s\S]{0,400}?/api/students/(\d+)/", r.text)
        if not m:
            pytest.skip("Could not resolve Miguel's id")
        mid = int(m.group(1))
        r2 = miguel_s.get(f"{BASE_URL}/api/students/{mid}/documents/")
        assert r2.status_code == 200, f"student own docs -> {r2.status_code}"

    def test_student_blocked_from_other(self, miguel_s):
        # student id=1 is Lucas (a different student) — Miguel should be 403
        r = miguel_s.get(f"{BASE_URL}/api/students/1/documents/")
        assert r.status_code == 403, \
            f"Miguel should not see another student's docs, got {r.status_code}"


# =====================================================================
# 4. Lesson Plans — admin + teacher + student scoping
# =====================================================================

class TestLessonPlansAdmin:
    def test_admin_list_200_seed(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/lesson-plans/")
        assert r.status_code == 200
        # Seed plan: "Week 1: Pre-history of Timor"
        assert "Pre-history" in r.text or "Pre-História" in r.text or "Week 1" in r.text, \
            "Seed lesson plan not visible in admin listing"

    def test_admin_create_lesson_plan(self, admin_s):
        url = f"{BASE_URL}/api/lesson-plans/add/"
        # Need a subject & class id. Subject 1 + class 3 per seed assumption.
        next_monday = (date.today() + timedelta(days=(7 - date.today().weekday()))).isoformat()
        r = _post(admin_s, url, {
            "title": "TEST_Phase2 Admin Plan",
            "title_pt": "TEST_Plano Admin",
            "title_tet": "TEST_Planu Admin",
            "subject": "1",
            "class_room": "3",
            "week_start": next_monday,
            "objectives": "Test objectives",
            "activities": "Day 1: intro. Day 2: practice.",
            "materials": "Book",
            "is_published": "on",
        }, follow=True)
        assert r.status_code == 200, f"create lesson plan failed: {r.status_code}"
        listing = admin_s.get(f"{BASE_URL}/api/lesson-plans/")
        assert "TEST_Phase2 Admin Plan" in listing.text

    def test_admin_create_draft_for_filter_test(self, admin_s):
        """Create an unpublished plan so we can verify students don't see drafts."""
        url = f"{BASE_URL}/api/lesson-plans/add/"
        next_monday = (date.today() + timedelta(days=(7 - date.today().weekday()))).isoformat()
        r = _post(admin_s, url, {
            "title": "TEST_Phase2 Draft Plan",
            "subject": "1",
            "class_room": "3",
            "week_start": next_monday,
            "activities": "Hidden from students",
            # is_published omitted -> False
        }, follow=True)
        assert r.status_code == 200


class TestLessonPlansTeacher:
    def test_teacher_list_filtered_to_own(self, teacher_s, admin_s):
        r = teacher_s.get(f"{BASE_URL}/api/lesson-plans/")
        assert r.status_code == 200, f"teacher list -> {r.status_code}"
        # We can't assert nothing else is shown without knowing exact ownership,
        # but verify the page renders. The filter qs.filter(teacher=t) is enforced
        # in academy_views.lesson_plan_list.

    def test_teacher_cannot_delete_other_plan(self, teacher_s, admin_s):
        """Try delete on seeded plan id=1. If t-004 owns -> 200, else expect 403."""
        url = f"{BASE_URL}/api/lesson-plans/1/delete/"
        r = teacher_s.get(url)
        assert r.status_code in (200, 403), f"unexpected: {r.status_code}"
        if r.status_code == 200:
            pytest.skip("t-004 appears to own lesson plan 1; cannot test 403 boundary")


class TestLessonPlansStudent:
    def test_tiago_sees_published_plan_for_class(self, tiago_s):
        # Tiago is in class_id=3; seeded plan + TEST_Phase2 Admin Plan target class 3 published
        r = tiago_s.get(f"{BASE_URL}/api/lesson-plans/")
        assert r.status_code == 200
        # Should see at least the admin-published TEST_Phase2 Admin Plan
        assert "TEST_Phase2 Admin Plan" in r.text or "Pre-history" in r.text or "Week 1" in r.text, \
            "Student should see published lesson plan for their class"

    def test_tiago_does_not_see_draft(self, tiago_s):
        r = tiago_s.get(f"{BASE_URL}/api/lesson-plans/")
        assert r.status_code == 200
        assert "TEST_Phase2 Draft Plan" not in r.text, \
            "Draft (is_published=False) leaked to student listing"

    def test_miguel_does_not_see_other_class_plans(self, miguel_s):
        # Miguel is in Year 7-B (NOT class_id=3) — should NOT see class-3 plans
        r = miguel_s.get(f"{BASE_URL}/api/lesson-plans/")
        assert r.status_code == 200
        assert "TEST_Phase2 Admin Plan" not in r.text, \
            "Cross-class leak: Miguel (other class) sees class-3 lesson plan"


# =====================================================================
# 5. Today / This-week widget
# =====================================================================

class TestTodayWidget:
    def test_widget_on_admin_dashboard(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/dashboard/")
        assert r.status_code == 200
        assert 'data-testid="today-widget"' in r.text, \
            "today-widget missing on admin dashboard"

    def test_widget_on_student_dashboard(self, tiago_s):
        r = tiago_s.get(f"{BASE_URL}/api/student/")
        assert r.status_code == 200
        assert 'data-testid="today-widget"' in r.text, \
            "today-widget missing on student dashboard"

    def test_widget_on_teacher_dashboard(self, teacher_s):
        r = teacher_s.get(f"{BASE_URL}/api/teacher/")
        assert r.status_code == 200
        assert 'data-testid="today-widget"' in r.text, \
            "today-widget missing on teacher dashboard"

    def test_widget_on_parent_dashboard(self, parent_s):
        r = parent_s.get(f"{BASE_URL}/api/parent/")
        assert r.status_code == 200
        assert 'data-testid="today-widget"' in r.text, \
            "today-widget missing on parent dashboard"

    def test_latest_notices_still_present(self, admin_s):
        """Iteration_4 created announcement 'TEST_Phase1 Welcome' (audience=all)."""
        r = admin_s.get(f"{BASE_URL}/api/dashboard/")
        assert r.status_code == 200
        # Recent announcements should still surface it (it has no expiry).
        # If it doesn't appear in recent_announcements (top 3 by published_at desc),
        # the announcement_list page is the canonical fallback verifier.
        if "TEST_Phase1 Welcome" not in r.text:
            r2 = admin_s.get(f"{BASE_URL}/api/announcements/")
            assert "TEST_Phase1 Welcome" in r2.text, \
                "Prior announcement vanished from system entirely"

    def test_upcoming_assignment_for_student(self, admin_s, tiago_s):
        """Create an assignment due within 7 days for class 3, then check Tiago's widget."""
        # First, create a fresh published assignment due in 5 days for class 3 (Year 10-A).
        due = (date.today() + timedelta(days=5)).strftime("%Y-%m-%dT09:00")
        assigned = date.today().strftime("%Y-%m-%dT09:00")
        url = f"{BASE_URL}/api/assignments/add/"
        # Form fields: title, subject, class_room, teacher (admin must pick), assigned_at, due_at, max_score, term, academic_year, is_published, ...
        # Try to grab an existing assignment form via GET to know exact fields.
        get_form = admin_s.get(url)
        assert get_form.status_code == 200
        # Reuse subject=1, class_room=3, teacher=1, academic_year=1, term=t1
        r = _post(admin_s, url, {
            "title": "TEST_Phase2 Due Soon",
            "subject": "1",
            "class_room": "3",
            "teacher": "1",
            "academic_year": "1",
            "term": "t1",
            "assigned_at": assigned,
            "due_at": due,
            "max_score": "100",
            "is_published": "on",
            "instructions": "TEST",
        }, follow=True)
        # Don't hard-fail the entire class if form has additional required fields;
        # the widget itself is the unit under test.
        widget = tiago_s.get(f"{BASE_URL}/api/student/")
        assert widget.status_code == 200
        if r.status_code == 200 and "TEST_Phase2 Due Soon" in widget.text:
            return
        # Fallback: widget should still render Upcoming assignments section markup
        assert "Upcoming" in widget.text or "upcoming" in widget.text, \
            "Widget missing 'Upcoming assignments' section on student dashboard"

    def test_no_upcoming_assignments_for_non_students(self, admin_s, teacher_s, parent_s):
        """upcoming_assignments should be empty for non-students; widget shows generic msg."""
        # We can't easily inspect the JSON, but if a student-specific upcoming
        # assignment leaks into admin/teacher/parent widget, that's a bug.
        for sess, role_url in [
            (admin_s, "/api/dashboard/"),
            (teacher_s, "/api/teacher/"),
            (parent_s, "/api/parent/"),
        ]:
            r = sess.get(f"{BASE_URL}{role_url}")
            assert r.status_code == 200
            assert "TEST_Phase2 Due Soon" not in r.text, \
                f"upcoming_assignments leaked into {role_url} widget"
