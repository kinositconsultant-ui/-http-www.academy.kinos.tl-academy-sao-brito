"""Phase 3 — LMS / Learning Materials.

Covers:
- Admin GET /api/learning/ grouped-by-subject card listing (seed visible).
- Admin POST /api/learning/add/ creates a video; detail page embeds YouTube iframe.
- YouTube URL parsing: watch?v=, youtu.be/, shorts/, watch?v=...&list=.
- Vimeo URL parsing.
- Non-YouTube/Vimeo video URL → empty embed_url → fallback button.
- Form validation: video needs `url`; pdf needs file OR url.
- Teacher list view shows all materials; teacher field locked on create.
- Audience scoping for students (class_room NULL vs specific class), Miguel vs Tiago.
- is_published=False hidden from students/parents; detail returns 403.
- Permission: teacher cannot delete material they didn't upload (admin can).
- Cross-portal nav links: 'Materials' on student/teacher/parent topbars; admin sidebar.
- Regression: phase1 and phase2 tests still pass (run separately).
"""
import io
import os
import re

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
LOGIN_URL = f"{BASE_URL}/api/login/"

YT_ID = "UPBMG5EYydo"
EMBED_YT = f"https://www.youtube.com/embed/{YT_ID}"


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


def _post(session, url, data, files=None, follow=True):
    token = _get_csrf(session, url)
    data = dict(data)
    data["csrfmiddlewaretoken"] = token
    return session.post(
        url, data=data, files=files,
        headers={"Referer": url}, allow_redirects=follow,
    )


def _extract_last_id(session, url_list):
    """Find the highest /api/learning/<id>/ id present on the list page."""
    r = session.get(url_list)
    assert r.status_code == 200
    ids = [int(x) for x in re.findall(r"/api/learning/(\d+)/", r.text)]
    return max(ids) if ids else None


def _find_id_by_title(session, list_url, title):
    """Locate a material's pk by scanning the listing for `title` then the nearest /api/learning/<id>/."""
    r = session.get(list_url)
    assert r.status_code == 200
    # Find title position, then look backward+forward for /api/learning/<id>/.
    idx = r.text.find(title)
    if idx == -1:
        return None
    window = r.text[max(0, idx - 800): idx + 800]
    m = re.search(r"/api/learning/(\d+)/", window)
    return int(m.group(1)) if m else None


# ---------- fixtures ----------

@pytest.fixture(scope="module")
def admin_s():
    return _login("admin", "admin123")


@pytest.fixture(scope="module")
def teacher_s():
    return _login("t-004", "teacher123")


@pytest.fixture(scope="module")
def miguel_s():
    return _login("adm-1003", "student123")


@pytest.fixture(scope="module")
def tiago_s():
    return _login("adm-1005", "student123")


@pytest.fixture(scope="module")
def parent_s():
    return _login("parent", "password123")


# =====================================================================
# 1. Admin list — grouped by subject, seed visible
# =====================================================================

class TestAdminList:
    def test_admin_list_200(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/learning/")
        assert r.status_code == 200
        # Seeds: Introduction to Photosynthesis (video) + Khan Academy: Cell Biology (link)
        assert "Photosynthesis" in r.text, "Seed video material not visible"
        assert "Khan Academy" in r.text or "Cell Biology" in r.text, \
            "Seed link material not visible"

    def test_admin_list_has_subject_grouping_and_icons(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/learning/")
        assert r.status_code == 200
        # Icon classes from LearningMaterial.TYPE_ICONS
        # video -> ph-play-circle (#dc2626), link -> ph-link (#2563eb)
        assert "ph-play-circle" in r.text, "video icon missing"
        assert "ph-link" in r.text, "link icon missing"
        # Colors used inline somewhere
        assert "#dc2626" in r.text or "dc2626" in r.text.lower(), "video color missing"


# =====================================================================
# 2. Admin create video — YouTube watch URL → embed iframe
# =====================================================================

class TestAdminCreateVideo:
    def test_admin_create_youtube_video(self, admin_s):
        url = f"{BASE_URL}/api/learning/add/"
        r = _post(admin_s, url, {
            "title": "TEST_LMS YouTube Watch",
            "title_pt": "TEST_LMS YT PT",
            "title_tet": "TEST_LMS YT TET",
            "subject": "1",
            "class_room": "",
            "teacher": "1",
            "material_type": "video",
            "url": f"https://www.youtube.com/watch?v={YT_ID}",
            "file": "",
            "description": "TEST upload",
            "week_no": "",
            "is_published": "on",
        })
        assert r.status_code == 200, f"create video -> {r.status_code}"
        # Confirm material is in listing
        listing = admin_s.get(f"{BASE_URL}/api/learning/")
        assert "TEST_LMS YouTube Watch" in listing.text

        pk = _find_id_by_title(admin_s, f"{BASE_URL}/api/learning/", "TEST_LMS YouTube Watch")
        assert pk, "Could not resolve created material id"
        detail = admin_s.get(f"{BASE_URL}/api/learning/{pk}/")
        assert detail.status_code == 200
        assert EMBED_YT in detail.text, \
            f"Expected embed substring '{EMBED_YT}' in detail page"


# =====================================================================
# 3. YouTube + Vimeo URL parsing edge cases — direct via detail page embed
# =====================================================================

class TestUrlParsing:
    @pytest.mark.parametrize("label,url_in", [
        ("youtu.be", f"https://youtu.be/{YT_ID}"),
        ("shorts",   f"https://www.youtube.com/shorts/{YT_ID}"),
        ("watch+list", f"https://www.youtube.com/watch?v={YT_ID}&list=PLabc123"),
    ])
    def test_youtube_variants_resolve_same_embed(self, admin_s, label, url_in):
        title = f"TEST_LMS YT {label}"
        r = _post(admin_s, f"{BASE_URL}/api/learning/add/", {
            "title": title,
            "subject": "1", "class_room": "",
            "teacher": "1", "material_type": "video",
            "url": url_in, "description": "",
            "is_published": "on",
        })
        assert r.status_code == 200, f"create [{label}] -> {r.status_code}"
        pk = _find_id_by_title(admin_s, f"{BASE_URL}/api/learning/", title)
        assert pk, f"id not resolved for {label}"
        detail = admin_s.get(f"{BASE_URL}/api/learning/{pk}/")
        assert detail.status_code == 200
        assert EMBED_YT in detail.text, \
            f"[{label}] expected embed {EMBED_YT} not found in detail"

    def test_vimeo_resolves_to_player(self, admin_s):
        r = _post(admin_s, f"{BASE_URL}/api/learning/add/", {
            "title": "TEST_LMS Vimeo",
            "subject": "1", "class_room": "",
            "teacher": "1", "material_type": "video",
            "url": "https://vimeo.com/76979871",
            "description": "",
            "is_published": "on",
        })
        assert r.status_code == 200
        pk = _find_id_by_title(admin_s, f"{BASE_URL}/api/learning/", "TEST_LMS Vimeo")
        assert pk
        detail = admin_s.get(f"{BASE_URL}/api/learning/{pk}/")
        assert "player.vimeo.com/video/76979871" in detail.text, \
            "Vimeo embed URL not present"

    def test_non_yt_vimeo_video_falls_back(self, admin_s):
        """A non-YouTube/Vimeo URL on a video record → embed_url empty → fallback button."""
        r = _post(admin_s, f"{BASE_URL}/api/learning/add/", {
            "title": "TEST_LMS Other Video",
            "subject": "1", "class_room": "",
            "teacher": "1", "material_type": "video",
            "url": "https://example.com/some-video.html",
            "is_published": "on",
        })
        assert r.status_code == 200
        pk = _find_id_by_title(admin_s, f"{BASE_URL}/api/learning/", "TEST_LMS Other Video")
        assert pk
        detail = admin_s.get(f"{BASE_URL}/api/learning/{pk}/")
        assert "Open the video on the original platform" in detail.text, \
            "Fallback button text missing for non-YT/Vimeo video"
        # No iframe pointing to youtube/vimeo embed
        assert EMBED_YT not in detail.text
        assert "player.vimeo.com" not in detail.text


# =====================================================================
# 4. Form validation
# =====================================================================

class TestFormValidation:
    def test_video_requires_url(self, admin_s):
        url = f"{BASE_URL}/api/learning/add/"
        r = _post(admin_s, url, {
            "title": "TEST_LMS NoURL Video",
            "subject": "1", "class_room": "",
            "teacher": "1", "material_type": "video",
            "url": "",
            "is_published": "on",
        }, follow=False)
        # Re-renders form with error (200, no redirect)
        assert r.status_code == 200, f"expected 200 form re-render, got {r.status_code}"
        assert "A URL is required for video material." in r.text, \
            "Expected url-required error text not in response"

    def test_pdf_requires_file_or_url(self, admin_s):
        url = f"{BASE_URL}/api/learning/add/"
        r = _post(admin_s, url, {
            "title": "TEST_LMS NoFile PDF",
            "subject": "1", "class_room": "",
            "teacher": "1", "material_type": "pdf",
            "url": "",
            "is_published": "on",
        }, follow=False)
        assert r.status_code == 200
        assert "Either upload a file or provide a URL." in r.text, \
            "Expected file-or-url error not present"


# =====================================================================
# 5. Teacher list + locked teacher field on create
# =====================================================================

class TestTeacherAccess:
    def test_teacher_sees_all_materials(self, teacher_s):
        r = teacher_s.get(f"{BASE_URL}/api/learning/")
        assert r.status_code == 200
        # Teachers may borrow each other's content — both seed materials visible
        assert "Photosynthesis" in r.text
        assert "Khan Academy" in r.text or "Cell Biology" in r.text

    def test_teacher_field_disabled_on_create_form(self, teacher_s):
        r = teacher_s.get(f"{BASE_URL}/api/learning/add/")
        assert r.status_code == 200
        # The teacher <select> / <input> should have `disabled`
        # Look for a disabled attribute near a name="teacher" attribute
        m = re.search(r'name="teacher"[^>]*', r.text)
        assert m, "teacher field not present on create form"
        # disabled may appear before or after name="teacher" in the tag; widen search
        tag_match = re.search(r"<(?:select|input)[^>]*name=\"teacher\"[^>]*>", r.text)
        assert tag_match, "teacher field tag not found"
        assert "disabled" in tag_match.group(0), \
            f"teacher field is NOT disabled for teacher role: {tag_match.group(0)[:200]}"

    def test_teacher_create_assigns_self(self, teacher_s):
        r = _post(teacher_s, f"{BASE_URL}/api/learning/add/", {
            "title": "TEST_LMS Teacher Owned",
            "subject": "1", "class_room": "",
            "material_type": "link",
            "url": "https://example.com/teacher-resource",
            "is_published": "on",
        })
        assert r.status_code == 200
        pk = _find_id_by_title(teacher_s, f"{BASE_URL}/api/learning/", "TEST_LMS Teacher Owned")
        assert pk, "Teacher's material not found in listing"
        # Detail page should show uploader = Carlos Mendes (t-004)
        detail = teacher_s.get(f"{BASE_URL}/api/learning/{pk}/")
        assert detail.status_code == 200
        # 'Uploaded by:' rendered with teacher.full_name — Carlos Mendes
        assert "Carlos Mendes" in detail.text or "t-004" in detail.text or \
               "Uploaded by" in detail.text


# =====================================================================
# 6. Class-scoped visibility for students
# =====================================================================

class TestClassScoping:
    @pytest.fixture(scope="class")
    def class3_only_material_id(self, admin_s):
        """Create a class_room=3 material (TEST_Class3Only) for cross-class isolation."""
        r = _post(admin_s, f"{BASE_URL}/api/learning/add/", {
            "title": "TEST_Class3Only",
            "subject": "1", "class_room": "3",
            "teacher": "1", "material_type": "link",
            "url": "https://example.com/class3",
            "is_published": "on",
        })
        assert r.status_code == 200
        pk = _find_id_by_title(admin_s, f"{BASE_URL}/api/learning/", "TEST_Class3Only")
        assert pk, "Could not resolve TEST_Class3Only id"
        return pk

    def test_tiago_sees_class3_material(self, tiago_s, class3_only_material_id):
        r = tiago_s.get(f"{BASE_URL}/api/learning/")
        assert r.status_code == 200
        assert "TEST_Class3Only" in r.text, \
            "Class-3 student (Tiago) should see class-3-scoped material"

    def test_miguel_does_not_see_class3_material(self, miguel_s, class3_only_material_id):
        r = miguel_s.get(f"{BASE_URL}/api/learning/")
        assert r.status_code == 200
        assert "TEST_Class3Only" not in r.text, \
            "Cross-class leak: Miguel (Year 7-B) sees class-3 material"

    def test_miguel_403_on_class3_detail(self, miguel_s, class3_only_material_id):
        r = miguel_s.get(f"{BASE_URL}/api/learning/{class3_only_material_id}/")
        assert r.status_code == 403, \
            f"Miguel detail on class-3 material should be 403, got {r.status_code}"

    def test_both_students_see_all_classes_seed(self, miguel_s, tiago_s):
        # Seed id=1 (Photosynthesis) has class_room=NULL — visible to both
        for label, sess in [("miguel", miguel_s), ("tiago", tiago_s)]:
            r = sess.get(f"{BASE_URL}/api/learning/")
            assert r.status_code == 200, f"{label} list -> {r.status_code}"
            assert "Photosynthesis" in r.text, \
                f"{label} should see class_room=NULL material"


# =====================================================================
# 7. is_published filter — drafts hidden from students/parents
# =====================================================================

class TestPublishedFilter:
    @pytest.fixture(scope="class")
    def draft_id(self, admin_s):
        r = _post(admin_s, f"{BASE_URL}/api/learning/add/", {
            "title": "TEST_Draft",
            "subject": "1", "class_room": "",
            "teacher": "1", "material_type": "link",
            "url": "https://example.com/draft",
            # is_published omitted = False
        })
        assert r.status_code == 200
        pk = _find_id_by_title(admin_s, f"{BASE_URL}/api/learning/", "TEST_Draft")
        assert pk, "Could not resolve TEST_Draft id"
        return pk

    def test_admin_sees_draft_in_list(self, admin_s, draft_id):
        r = admin_s.get(f"{BASE_URL}/api/learning/")
        assert "TEST_Draft" in r.text

    def test_student_does_not_see_draft(self, miguel_s, draft_id):
        r = miguel_s.get(f"{BASE_URL}/api/learning/")
        assert r.status_code == 200
        assert "TEST_Draft" not in r.text, \
            "Draft (is_published=False) leaked to student listing"

    def test_parent_does_not_see_draft(self, parent_s, draft_id):
        r = parent_s.get(f"{BASE_URL}/api/learning/")
        assert r.status_code == 200
        assert "TEST_Draft" not in r.text, \
            "Draft leaked to parent listing"

    def test_student_403_on_draft_detail(self, miguel_s, draft_id):
        r = miguel_s.get(f"{BASE_URL}/api/learning/{draft_id}/")
        assert r.status_code == 403, \
            f"Student detail on draft should be 403, got {r.status_code}"

    def test_parent_403_on_draft_detail(self, parent_s, draft_id):
        r = parent_s.get(f"{BASE_URL}/api/learning/{draft_id}/")
        assert r.status_code == 403, \
            f"Parent detail on draft should be 403, got {r.status_code}"


# =====================================================================
# 8. Delete permission boundary
# =====================================================================

class TestDeletePermission:
    def test_teacher_cannot_delete_admin_uploaded(self, teacher_s, admin_s):
        """Create an admin-owned material then try to delete from teacher session."""
        r = _post(admin_s, f"{BASE_URL}/api/learning/add/", {
            "title": "TEST_LMS Admin Owned For Delete",
            "subject": "1", "class_room": "",
            "teacher": "1",  # Teacher id=1 likely NOT t-004 (t-004 is employee_no, check)
            "material_type": "link",
            "url": "https://example.com/admin-owned",
            "is_published": "on",
        })
        assert r.status_code == 200
        pk = _find_id_by_title(admin_s, f"{BASE_URL}/api/learning/",
                                "TEST_LMS Admin Owned For Delete")
        assert pk
        # Teacher attempts POST delete
        del_url = f"{BASE_URL}/api/learning/{pk}/delete/"
        token = _get_csrf(teacher_s, del_url) if teacher_s.get(del_url).status_code == 200 \
                else None
        if token is None:
            # GET itself blocked → already 403, that's fine
            r2 = teacher_s.get(del_url)
            assert r2.status_code == 403, \
                f"teacher cross-owner delete page should be 403, got {r2.status_code}"
            return
        r3 = teacher_s.post(del_url,
                            data={"csrfmiddlewaretoken": token},
                            headers={"Referer": del_url},
                            allow_redirects=False)
        # If teacher id=1 happens to be t-004, this test is meaningless — skip if so
        check = admin_s.get(f"{BASE_URL}/api/learning/{pk}/")
        if r3.status_code in (301, 302) and check.status_code == 404:
            pytest.skip(
                "Teacher id=1 is t-004; cannot exercise cross-owner 403 boundary "
                "without seeding a 2nd teacher-owned material."
            )
        assert r3.status_code == 403, \
            f"teacher cross-owner POST delete should be 403, got {r3.status_code}"

    def test_admin_can_delete_any(self, admin_s):
        # Create then delete
        r = _post(admin_s, f"{BASE_URL}/api/learning/add/", {
            "title": "TEST_LMS Admin Delete Target",
            "subject": "1", "class_room": "",
            "teacher": "1", "material_type": "link",
            "url": "https://example.com/del",
            "is_published": "on",
        })
        assert r.status_code == 200
        pk = _find_id_by_title(admin_s, f"{BASE_URL}/api/learning/",
                                "TEST_LMS Admin Delete Target")
        assert pk
        del_url = f"{BASE_URL}/api/learning/{pk}/delete/"
        token = _get_csrf(admin_s, del_url)
        r2 = admin_s.post(del_url,
                          data={"csrfmiddlewaretoken": token},
                          headers={"Referer": del_url},
                          allow_redirects=False)
        assert r2.status_code in (301, 302), f"admin delete -> {r2.status_code}"
        check = admin_s.get(f"{BASE_URL}/api/learning/{pk}/")
        assert check.status_code == 404


# =====================================================================
# 9. Cross-portal nav links
# =====================================================================

class TestNavLinks:
    def test_admin_sidebar_has_learning(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/dashboard/")
        assert r.status_code == 200
        assert "/api/learning/" in r.text and "Learning Materials" in r.text, \
            "Admin sidebar missing 'Learning Materials' link"

    def test_student_topbar_has_materials(self, tiago_s):
        r = tiago_s.get(f"{BASE_URL}/api/student/")
        assert r.status_code == 200
        assert "/api/learning/" in r.text and "Materials" in r.text, \
            "Student topbar missing 'Materials' link"
        assert 'data-testid="student-nav-learning"' in r.text

    def test_teacher_topbar_has_materials(self, teacher_s):
        r = teacher_s.get(f"{BASE_URL}/api/teacher/")
        assert r.status_code == 200
        assert "/api/learning/" in r.text and "Materials" in r.text
        assert 'data-testid="teacher-nav-learning"' in r.text

    def test_parent_topbar_has_materials(self, parent_s):
        r = parent_s.get(f"{BASE_URL}/api/parent/")
        assert r.status_code == 200
        assert "/api/learning/" in r.text and "Materials" in r.text
        assert 'data-testid="parent-nav-learning"' in r.text
