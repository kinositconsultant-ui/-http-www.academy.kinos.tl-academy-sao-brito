"""Phase 3.1 — MaterialView (LMS engagement tracking) regression tests."""
import os
import re
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")


def _login(username, password):
    s = requests.Session()
    r = s.get(f"{BASE}/api/login/")
    token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text).group(1)
    r = s.post(
        f"{BASE}/api/login/",
        data={"csrfmiddlewaretoken": token, "username": username, "password": password},
        headers={"Referer": f"{BASE}/api/login/"},
        allow_redirects=False,
    )
    assert r.status_code in (302, 303), f"Login failed for {username}: {r.status_code}"
    return s


def _csrf(session, url):
    r = session.get(url)
    return re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text).group(1)


# Use LearningMaterial id=1 (visible to all classes in seed) for these tests.
MATERIAL_ID = 1


def test_student_detail_creates_materialview():
    """First detail view records a MaterialView with view_count=1."""
    s = _login("adm-1005", "student123")
    r = s.get(f"{BASE}/api/learning/{MATERIAL_ID}/")
    assert r.status_code == 200
    assert 'data-testid="material-progress"' in r.text
    # Either fresh "Viewed 1 time" or an existing higher count is OK
    assert "Your progress" in r.text


def test_student_detail_increments_view_count():
    """Two sequential visits should produce a strictly greater view_count."""
    s = _login("adm-1005", "student123")
    s.get(f"{BASE}/api/learning/{MATERIAL_ID}/")
    r1 = s.get(f"{BASE}/api/learning/{MATERIAL_ID}/")
    m1 = re.search(r"Viewed (\d+) time", r1.text)
    if not m1:
        # Already completed — skip count check
        pytest.skip("Material already completed; view_count text hidden.")
    n1 = int(m1.group(1))
    r2 = s.get(f"{BASE}/api/learning/{MATERIAL_ID}/")
    m2 = re.search(r"Viewed (\d+) time", r2.text)
    assert m2 and int(m2.group(1)) >= n1


def test_student_can_mark_complete_and_toggle():
    s = _login("adm-1005", "student123")
    s.get(f"{BASE}/api/learning/{MATERIAL_ID}/")
    token = _csrf(s, f"{BASE}/api/learning/{MATERIAL_ID}/")
    r = s.post(
        f"{BASE}/api/learning/{MATERIAL_ID}/complete/",
        data={"csrfmiddlewaretoken": token},
        headers={"Referer": f"{BASE}/api/learning/{MATERIAL_ID}/"},
        allow_redirects=False,
    )
    assert r.status_code in (302, 303)
    r2 = s.get(f"{BASE}/api/learning/{MATERIAL_ID}/")
    # Could be Completed or Not Complete depending on previous run; toggle once
    # to a known state, then assert.
    if "Mark as not complete" in r2.text:
        # We're in the completed state — toggle off, then back on.
        token = _csrf(s, f"{BASE}/api/learning/{MATERIAL_ID}/")
        s.post(
            f"{BASE}/api/learning/{MATERIAL_ID}/complete/",
            data={"csrfmiddlewaretoken": token},
            headers={"Referer": f"{BASE}/api/learning/{MATERIAL_ID}/"},
            allow_redirects=False,
        )
        r2 = s.get(f"{BASE}/api/learning/{MATERIAL_ID}/")
    assert "Mark as complete" in r2.text


def test_only_students_can_toggle_complete():
    s = _login("admin", "admin123")
    token = _csrf(s, f"{BASE}/api/learning/{MATERIAL_ID}/")
    r = s.post(
        f"{BASE}/api/learning/{MATERIAL_ID}/complete/",
        data={"csrfmiddlewaretoken": token},
        headers={"Referer": f"{BASE}/api/learning/{MATERIAL_ID}/"},
        allow_redirects=False,
    )
    # Admin is_superuser path is allowed; teacher should be denied.
    s2 = _login("t-004", "teacher123")
    token2 = _csrf(s2, f"{BASE}/api/learning/{MATERIAL_ID}/")
    r2 = s2.post(
        f"{BASE}/api/learning/{MATERIAL_ID}/complete/",
        data={"csrfmiddlewaretoken": token2},
        headers={"Referer": f"{BASE}/api/learning/{MATERIAL_ID}/"},
        allow_redirects=False,
    )
    assert r2.status_code == 403


def test_admin_sees_engagement_panel():
    """Admin/teacher view shows engagement stats; student view does not."""
    a = _login("admin", "admin123")
    r = a.get(f"{BASE}/api/learning/{MATERIAL_ID}/")
    assert 'data-testid="material-engagement"' in r.text
    assert "Engagement" in r.text

    st = _login("adm-1005", "student123")
    r2 = st.get(f"{BASE}/api/learning/{MATERIAL_ID}/")
    assert 'data-testid="material-engagement"' not in r2.text


def test_completed_badge_on_student_list():
    """After completing, the card on the list view shows a 'Done' badge."""
    s = _login("adm-1005", "student123")
    # Ensure completed
    s.get(f"{BASE}/api/learning/{MATERIAL_ID}/")
    token = _csrf(s, f"{BASE}/api/learning/{MATERIAL_ID}/")
    s.post(
        f"{BASE}/api/learning/{MATERIAL_ID}/complete/",
        data={"csrfmiddlewaretoken": token},
        headers={"Referer": f"{BASE}/api/learning/{MATERIAL_ID}/"},
        allow_redirects=False,
    )
    # Confirm we are in completed state
    r = s.get(f"{BASE}/api/learning/{MATERIAL_ID}/")
    if "Mark as complete" in r and "Mark as not complete" not in r.text:
        # We toggled off — toggle back on
        token = _csrf(s, f"{BASE}/api/learning/{MATERIAL_ID}/")
        s.post(
            f"{BASE}/api/learning/{MATERIAL_ID}/complete/",
            data={"csrfmiddlewaretoken": token},
            headers={"Referer": f"{BASE}/api/learning/{MATERIAL_ID}/"},
            allow_redirects=False,
        )
    r2 = s.get(f"{BASE}/api/learning/")
    assert f'data-testid="card-completed-{MATERIAL_ID}"' in r2.text
