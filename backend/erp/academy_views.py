"""Phase 1 — Assignments, Announcements, Calendar.

Audience-aware list endpoints used by admin / teacher / student / parent
portals. Keep handlers small; mirror the conventions of views.py.
"""
from datetime import datetime, time
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.models import School
from .forms import (
    AssignmentForm, AssignmentGradeForm, StudentSubmissionForm,
    AnnouncementForm, CalendarEventForm,
)
from .models import (
    Assignment, AssignmentSubmission, Announcement, CalendarEvent,
    Student, Teacher, Grade, SchoolClass,
)


def _is_staff(u):
    return u.is_authenticated and (
        u.is_superuser or u.role in ("admin", "principal", "accountant", "hr"))


def _is_teacher(u):
    return u.is_authenticated and (
        u.is_superuser or u.role in ("teacher", "admin", "principal"))


def _base_template_for(user):
    """Pick the right base template depending on the viewer's role so the
    portal pages don't render the admin sidebar for students/parents/teachers."""
    role = getattr(user, "role", "")
    if user.is_superuser or role in ("admin", "principal", "accountant", "hr"):
        return "dashboard_base.html"
    if role == "teacher":
        return "teacher_base.html"
    if role == "parent":
        return "parent_base.html"
    if role == "student":
        return "student_base.html"
    return "dashboard_base.html"


# ---------------------------------------------------------------------
# Audience filter
# ---------------------------------------------------------------------

def _filter_for_user(qs, user):
    """Filter Announcement / CalendarEvent qs by audience for the given user."""
    role = getattr(user, "role", "")
    if user.is_superuser or role in ("admin", "principal"):
        return qs
    audience_filter = Q(audience="all") | Q(audience=role)
    qs = qs.filter(audience_filter)

    # If the user is a student/parent, also intersect by class
    class_ids = []
    if role == "student":
        st = Student.objects.filter(student_user=user).first()
        if st and st.school_class_id:
            class_ids = [st.school_class_id]
    elif role == "parent":
        class_ids = list(Student.objects.filter(parent_users=user)
                         .values_list("school_class_id", flat=True))
    elif role == "teacher":
        t = Teacher.objects.filter(teacher_user=user).first()
        if t:
            class_ids = list(SchoolClass.objects.filter(
                subjects__in=t.subjects.all()).distinct().values_list("id", flat=True))

    if class_ids:
        # match items with no class restriction OR matching one of our classes
        qs = qs.filter(Q(audience_classes__isnull=True) |
                       Q(audience_classes__in=class_ids)).distinct()
    else:
        # no classes known — show only unrestricted ones
        qs = qs.filter(audience_classes__isnull=True).distinct()
    return qs


# =====================================================================
# Assignments — admin / teacher CRUD
# =====================================================================

@login_required
def assignment_list(request):
    u = request.user
    qs = Assignment.objects.select_related("subject", "class_room", "teacher")
    role = getattr(u, "role", "")
    if not (u.is_superuser or role in ("admin", "principal")):
        if role == "teacher":
            t = Teacher.objects.filter(teacher_user=u).first()
            qs = qs.filter(teacher=t) if t else qs.none()
        else:
            return HttpResponseForbidden("Admins / teachers only.")
    return render(request, "erp/academy/assignment_list.html", {
        "items": qs,
        "school": School.get_active(),
    })


@login_required
def assignment_create(request):
    u = request.user
    if not _is_teacher(u):
        return HttpResponseForbidden("Teachers / admins only.")
    initial = {}
    if getattr(u, "role", "") == "teacher":
        t = Teacher.objects.filter(teacher_user=u).first()
        if t:
            initial["teacher"] = t
    form = AssignmentForm(request.POST or None, request.FILES or None, initial=initial)
    if form.is_valid():
        a = form.save()
        messages.success(request, f"Assignment '{a.title}' created.")
        return redirect("assignment_detail", pk=a.pk)
    return render(request, "erp/form.html", {
        "form": form, "title": "New assignment", "back": "assignment_list"})


@login_required
def assignment_detail(request, pk):
    u = request.user
    a = get_object_or_404(Assignment, pk=pk)
    role = getattr(u, "role", "")
    if not (u.is_superuser or role in ("admin", "principal")
            or (role == "teacher" and a.teacher and a.teacher.teacher_user_id == u.id)):
        return HttpResponseForbidden("Not allowed.")
    submissions = a.submissions.select_related("student").order_by("-submitted_at")
    # roster of expected students = class roster minus those who already submitted
    submitted_ids = set(submissions.values_list("student_id", flat=True))
    missing = a.class_room.students.exclude(id__in=submitted_ids)
    return render(request, "erp/academy/assignment_detail.html", {
        "a": a, "submissions": submissions, "missing": missing,
        "school": School.get_active(),
    })


@login_required
def assignment_delete(request, pk):
    a = get_object_or_404(Assignment, pk=pk)
    u = request.user
    role = getattr(u, "role", "")
    if not (u.is_superuser or role in ("admin", "principal")
            or (role == "teacher" and a.teacher and a.teacher.teacher_user_id == u.id)):
        return HttpResponseForbidden("Not allowed.")
    if request.method == "POST":
        a.delete()
        messages.success(request, "Assignment deleted.")
        return redirect("assignment_list")
    return render(request, "erp/confirm_delete.html",
                  {"object": a, "back": "assignment_list"})


@login_required
def submission_grade(request, pk):
    """Teacher / admin grades a single submission."""
    sub = get_object_or_404(AssignmentSubmission.objects.select_related(
        "assignment", "student"), pk=pk)
    a = sub.assignment
    u = request.user
    role = getattr(u, "role", "")
    if not (u.is_superuser or role in ("admin", "principal")
            or (role == "teacher" and a.teacher and a.teacher.teacher_user_id == u.id)):
        return HttpResponseForbidden("Not allowed.")
    form = AssignmentGradeForm(request.POST or None, instance=sub)
    if form.is_valid():
        s = form.save(commit=False)
        s.graded_at = timezone.now()
        s.graded_by = u
        s.save()
        if form.cleaned_data.get("create_grade_entry") and s.score is not None:
            Grade.objects.create(
                student=s.student, subject=a.subject,
                academic_year=a.academic_year,
                semester=a.term, exam_name=f"Assignment: {a.title}",
                score=s.score, total=a.max_score, passing_pct=50,
            )
            messages.success(request, "Submission graded · Grade entry created for the report card.")
        else:
            messages.success(request, "Submission graded.")
        return redirect("assignment_detail", pk=a.pk)
    return render(request, "erp/academy/submission_grade.html", {
        "form": form, "sub": sub, "a": a, "school": School.get_active()})


# =====================================================================
# Assignments — student side
# =====================================================================

@login_required
def student_assignments(request):
    u = request.user
    if getattr(u, "role", "") != "student" and not u.is_superuser:
        return HttpResponseForbidden("Students only.")
    st = Student.objects.filter(student_user=u).first()
    if not st:
        return HttpResponseForbidden("No student profile for this user.")
    assignments = Assignment.objects.filter(
        class_room=st.school_class, is_published=True
    ).select_related("subject", "teacher").order_by("-assigned_at")
    # annotate each with the student's submission (if any)
    my_subs = {s.assignment_id: s for s in AssignmentSubmission.objects.filter(
        student=st, assignment__in=assignments)}
    rows = [{"a": a, "sub": my_subs.get(a.id)} for a in assignments]
    return render(request, "erp/academy/student_assignments.html", {
        "rows": rows, "student": st, "school": School.get_active()})


@login_required
def student_submit(request, pk):
    u = request.user
    if getattr(u, "role", "") != "student" and not u.is_superuser:
        return HttpResponseForbidden("Students only.")
    st = Student.objects.filter(student_user=u).first()
    if not st:
        return HttpResponseForbidden("No student profile.")
    a = get_object_or_404(Assignment, pk=pk, is_published=True, class_room=st.school_class)
    sub, _ = AssignmentSubmission.objects.get_or_create(assignment=a, student=st)
    form = StudentSubmissionForm(request.POST or None, request.FILES or None, instance=sub)
    if form.is_valid():
        s = form.save(commit=False)
        # If they're updating an already-graded submission, clear the grade.
        if s.score is not None and (form.changed_data and ("text_answer" in form.changed_data or "file" in form.changed_data)):
            s.score = None
            s.feedback = ""
            s.graded_at = None
        s.save()
        messages.success(request, "Submission saved.")
        return redirect("student_assignments")
    return render(request, "erp/academy/student_submit.html", {
        "form": form, "a": a, "sub": sub, "school": School.get_active()})


# =====================================================================
# Announcements
# =====================================================================

@login_required
def announcement_list(request):
    u = request.user
    qs = Announcement.objects.all()
    if not _is_staff(u):
        qs = _filter_for_user(qs, u).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gte=timezone.now()))
    return render(request, "erp/academy/announcement_list.html", {
        "items": qs, "school": School.get_active(),
        "base_template": _base_template_for(u),
        "can_manage": _is_staff(u) and u.role != "hr",
    })


@login_required
def announcement_create(request):
    u = request.user
    if not (u.is_superuser or u.role in ("admin", "principal", "accountant")):
        return HttpResponseForbidden("Admins only.")
    form = AnnouncementForm(request.POST or None)
    if form.is_valid():
        a = form.save(commit=False)
        a.author = u
        a.save()
        form.save_m2m()
        if form.cleaned_data.get("send_email"):
            _send_announcement_email(a)
        messages.success(request, "Announcement published.")
        return redirect("announcement_list")
    return render(request, "erp/form.html", {
        "form": form, "title": "New announcement", "back": "announcement_list"})


@login_required
def announcement_delete(request, pk):
    if not (request.user.is_superuser or request.user.role in ("admin", "principal")):
        return HttpResponseForbidden("Admins only.")
    obj = get_object_or_404(Announcement, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Announcement removed.")
        return redirect("announcement_list")
    return render(request, "erp/confirm_delete.html",
                  {"object": obj, "back": "announcement_list"})


def _send_announcement_email(ann):
    """Send via the existing erp/mail.py hook (LIVE if SendGrid keys set, else MOCKED)."""
    from .mail import send_email
    from accounts.models import User

    target_qs = User.objects.exclude(email="")
    if ann.audience != "all":
        target_qs = target_qs.filter(role=ann.audience)
    recipients = list(target_qs.values_list("email", flat=True))
    if not recipients:
        return
    school = School.get_active()
    subject = f"[{(school.name if school else 'Academy')}] {ann.title}"
    html = f"<p>{ann.body}</p>"
    if ann.body_pt:
        html += f"<hr><p><b>PT</b></p><p>{ann.body_pt}</p>"
    if ann.body_tet:
        html += f"<hr><p><b>TET</b></p><p>{ann.body_tet}</p>"
    for email in recipients:
        send_email(email, subject, html)
    ann.email_sent = True
    ann.email_sent_at = timezone.now()
    ann.save(update_fields=["email_sent", "email_sent_at"])


# =====================================================================
# Calendar
# =====================================================================

@login_required
def calendar_view(request):
    u = request.user
    qs = CalendarEvent.objects.all()
    if not _is_staff(u):
        qs = _filter_for_user(qs, u)

    # Default month window
    today = timezone.now().date()
    month = int(request.GET.get("m") or today.month)
    year = int(request.GET.get("y") or today.year)
    # range
    start = datetime.combine(today.replace(year=year, month=month, day=1), time.min)
    if month == 12:
        end_year, end_month = year + 1, 1
    else:
        end_year, end_month = year, month + 1
    end = datetime.combine(today.replace(year=end_year, month=end_month, day=1), time.min)
    events = list(qs.filter(start_at__gte=start, start_at__lt=end))

    # group by day for the month grid
    by_day = {}
    for e in events:
        key = e.start_at.date().isoformat()
        by_day.setdefault(key, []).append(e)

    return render(request, "erp/academy/calendar.html", {
        "events": events,
        "by_day": by_day,
        "year": year, "month": month,
        "today": today,
        "school": School.get_active(),
        "base_template": _base_template_for(u),
        "can_manage": _is_staff(u) and u.role != "hr",
    })


@login_required
def event_create(request):
    u = request.user
    if not (u.is_superuser or u.role in ("admin", "principal")):
        return HttpResponseForbidden("Admins only.")
    form = CalendarEventForm(request.POST or None)
    if form.is_valid():
        e = form.save(commit=False)
        e.created_by = u
        e.save()
        form.save_m2m()
        messages.success(request, "Event added.")
        return redirect("calendar_view")
    return render(request, "erp/form.html", {
        "form": form, "title": "New event", "back": "calendar_view"})


@login_required
def event_delete(request, pk):
    if not (request.user.is_superuser or request.user.role in ("admin", "principal")):
        return HttpResponseForbidden("Admins only.")
    obj = get_object_or_404(CalendarEvent, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Event removed.")
        return redirect("calendar_view")
    return render(request, "erp/confirm_delete.html",
                  {"object": obj, "back": "calendar_view"})
