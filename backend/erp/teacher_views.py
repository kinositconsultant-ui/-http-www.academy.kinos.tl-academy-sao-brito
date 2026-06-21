"""Teacher self-service portal.

A teacher logs in with `role=teacher` credentials and:
 - sees only the classes/subjects they are assigned to (via Teacher.subjects)
 - marks attendance for students in those classes
 - enters/edits grades for those subjects
 - writes evaluations & advice for students (visible to parents by default)
 - views their own profile, payslips, training history, and leave requests
"""
from datetime import date
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.models import School
from .models import (
    Teacher, Student, SchoolClass, Subject, AcademicYear,
    Grade, Attendance, SalaryPayment, LeaveRequest,
    TrainingEnrollment, StudentEvaluation, TeachingDocument,
)
from .forms import LeaveRequestForm


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _teacher_only(user):
    return user.is_authenticated and (user.role == "teacher" or user.is_superuser)


def _my_teacher(user):
    return Teacher.objects.filter(teacher_user=user).prefetch_related("subjects").first()


def _my_subjects(teacher):
    return teacher.subjects.select_related("school_class").all()


def _my_classes(teacher):
    """SchoolClasses the teacher is assigned to (via subjects)."""
    return SchoolClass.objects.filter(
        subjects__in=teacher.subjects.all()
    ).distinct()


def _my_students(teacher):
    return Student.objects.filter(
        school_class__in=_my_classes(teacher), is_active=True
    ).select_related("school_class")


def _gate(request):
    """Return (teacher, response_or_none). Use at top of every view."""
    if not _teacher_only(request.user):
        return None, redirect("/api/post-login/")
    teacher = _my_teacher(request.user)
    if not teacher:
        return None, render(request, "erp/teacher_no_link.html", {})
    return teacher, None


# ---------------------------------------------------------------------
# Dashboard / Overview
# ---------------------------------------------------------------------

@login_required
def teacher_dashboard(request):
    """Legacy overview — now redirects straight to Attendance (the daily task)."""
    teacher, redir = _gate(request)
    if redir:
        return redir
    return redirect("/api/teacher/attendance/")


@login_required
def teacher_students(request):
    """Read-only roster of every student in the subjects I teach."""
    teacher, redir = _gate(request)
    if redir:
        return redir
    students = list(_my_students(teacher).order_by(
        "school_class__name", "first_name"))
    # Compute attendance % per student
    today_year = date.today().year
    rows = []
    for s in students:
        att = s.attendance.filter(date__year=today_year)
        total = att.count()
        present = att.filter(status="present").count()
        att_pct = round(100 * present / total, 1) if total else None
        avg = s.grades.aggregate(a=Avg("score"))["a"]
        rows.append({"student": s, "att_pct": att_pct,
                     "avg": round(float(avg), 1) if avg else None})
    return render(request, "erp/teacher_students.html", {
        "teacher": teacher, "school": School.get_active(),
        "rows": rows, "subjects": _my_subjects(teacher),
    })


# ---------------------------------------------------------------------
# Attendance entry
# ---------------------------------------------------------------------

@login_required
def teacher_attendance(request):
    teacher, redir = _gate(request)
    if redir:
        return redir
    classes = _my_classes(teacher)
    class_id = request.GET.get("class") or request.POST.get("class")
    the_date = request.GET.get("date") or request.POST.get("date") or str(date.today())
    selected = classes.filter(id=class_id).first() if class_id else classes.first()
    students = []
    rows = []
    if selected:
        students = list(Student.objects.filter(
            school_class=selected, is_active=True).order_by("first_name"))
        existing = {a.student_id: a for a in Attendance.objects.filter(
            student__in=students, date=the_date)}
        rows = [(s, existing.get(s.id)) for s in students]

    if request.method == "POST" and selected:
        for s in students:
            status_val = request.POST.get(f"status_{s.id}")
            if not status_val:
                continue
            existing_row = Attendance.objects.filter(student=s, date=the_date).first()
            if existing_row:
                existing_row.status = status_val
                existing_row.save(update_fields=["status"])
            else:
                Attendance.objects.create(
                    student=s, date=the_date, status=status_val,
                    recorded_by=request.user)
        messages.success(request, f"Attendance saved for {selected} on {the_date}.")
        return redirect(f"/api/teacher/attendance/?class={selected.id}&date={the_date}")

    return render(request, "erp/teacher_attendance.html", {
        "teacher": teacher, "classes": classes, "selected": selected,
        "the_date": the_date, "rows": rows,
    })


# ---------------------------------------------------------------------
# Grades (enter / edit)
# ---------------------------------------------------------------------

@login_required
def teacher_grades(request):
    teacher, redir = _gate(request)
    if redir:
        return redir
    subjects = _my_subjects(teacher)
    years = AcademicYear.objects.all()
    subject_id = request.GET.get("subject")
    year_id = request.GET.get("year")
    semester = request.GET.get("semester") or "s1"
    exam_name = request.GET.get("exam_name", "Term assessment")

    selected_subject = subjects.filter(id=subject_id).first() if subject_id else None
    selected_year = (years.filter(id=year_id).first() if year_id
                     else AcademicYear.objects.filter(is_current=True).first())

    students = []
    grade_rows = []
    if selected_subject and selected_year:
        students = list(Student.objects.filter(
            school_class=selected_subject.school_class, is_active=True
        ).order_by("first_name"))
        existing = {}
        for g in Grade.objects.filter(
                subject=selected_subject, academic_year=selected_year,
                semester=semester, exam_name=exam_name,
                student__in=students):
            existing[g.student_id] = g
        grade_rows = [(s, existing.get(s.id)) for s in students]

    if request.method == "POST" and selected_subject and selected_year:
        exam_name = request.POST.get("exam_name") or exam_name
        semester = request.POST.get("semester") or semester
        total = int(request.POST.get("total") or 100)
        saved = 0
        for s in students:
            raw = request.POST.get(f"score_{s.id}", "").strip()
            if raw == "":
                continue
            try:
                score = float(raw)
            except ValueError:
                continue
            row = next((g for s2, g in grade_rows if s2.id == s.id), None)
            if row:
                row.score = score
                row.total = total
                row.exam_name = exam_name
                row.save()
            else:
                Grade.objects.create(
                    student=s, subject=selected_subject,
                    class_group=selected_subject.school_class,
                    academic_year=selected_year, semester=semester,
                    exam_name=exam_name, score=score, total=total,
                    recorded_by=request.user)
            saved += 1
        messages.success(request, f"{saved} grade(s) saved.")
        return redirect(f"/api/teacher/grades/?subject={selected_subject.id}"
                        f"&year={selected_year.id}&semester={semester}"
                        f"&exam_name={exam_name}")

    return render(request, "erp/teacher_grades.html", {
        "teacher": teacher, "subjects": subjects, "years": years,
        "selected_subject": selected_subject, "selected_year": selected_year,
        "semester": semester, "exam_name": exam_name,
        "grade_rows": grade_rows,
    })


# ---------------------------------------------------------------------
# Evaluations & Advice
# ---------------------------------------------------------------------

@login_required
def teacher_evaluations(request):
    teacher, redir = _gate(request)
    if redir:
        return redir
    rows = (StudentEvaluation.objects.filter(teacher=teacher)
            .select_related("student", "academic_year"))
    return render(request, "erp/teacher_evaluations.html", {
        "teacher": teacher, "rows": rows,
    })


@login_required
def teacher_evaluation_add(request):
    teacher, redir = _gate(request)
    if redir:
        return redir
    students = _my_students(teacher)
    if request.method == "POST":
        student_id = request.POST.get("student")
        student = students.filter(id=student_id).first()
        if not student:
            messages.error(request, "Pick one of your students.")
        else:
            StudentEvaluation.objects.create(
                student=student, teacher=teacher,
                academic_year=AcademicYear.objects.filter(is_current=True).first(),
                semester=request.POST.get("semester", "s1"),
                category=request.POST.get("category", "academic"),
                comment=request.POST.get("comment", "").strip(),
                recommendation=request.POST.get("recommendation", "").strip(),
                visible_to_parent=bool(request.POST.get("visible_to_parent")),
            )
            messages.success(request, "Evaluation saved.")
            return redirect("teacher_evaluations")
    return render(request, "erp/teacher_evaluation_form.html", {
        "teacher": teacher, "students": students,
    })


@login_required
def teacher_evaluation_delete(request, pk):
    teacher, redir = _gate(request)
    if redir:
        return redir
    ev = get_object_or_404(StudentEvaluation, pk=pk, teacher=teacher)
    if request.method == "POST":
        ev.delete()
        messages.success(request, "Evaluation deleted.")
    return redirect("teacher_evaluations")


# ---------------------------------------------------------------------
# My Profile (read-only + payslips + training + leaves)
# ---------------------------------------------------------------------

@login_required
def teacher_profile(request):
    teacher, redir = _gate(request)
    if redir:
        return redir
    payslips = SalaryPayment.objects.filter(teacher=teacher).order_by("-paid_date", "-id")[:12]
    enrollments = TrainingEnrollment.objects.filter(employee__email=teacher.email
                                                    ).select_related("program") if teacher.email else []
    # leaves only if the teacher has an Employee row matching email
    leaves = LeaveRequest.objects.filter(employee__email=teacher.email
                                         ).order_by("-start_date") if teacher.email else []
    return render(request, "erp/teacher_profile.html", {
        "teacher": teacher, "school": School.get_active(),
        "payslips": payslips, "enrollments": enrollments, "leaves": leaves,
    })


@login_required
def teacher_leave_request(request):
    """Teacher submits a leave request from their portal."""
    teacher, redir = _gate(request)
    if redir:
        return redir
    from .models import Employee
    emp = Employee.objects.filter(email=teacher.email).first() if teacher.email else None
    if not emp:
        messages.error(request,
                       "No HR employee record matches your email. Ask admin to link one.")
        return redirect("teacher_profile")
    if request.method == "POST":
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.employee = emp
            obj.status = "pending"
            obj.save()
            messages.success(request, "Leave request submitted for approval.")
            return redirect("teacher_profile")
    else:
        form = LeaveRequestForm(initial={"employee": emp})
    return render(request, "erp/form.html",
                  {"form": form, "title": "Apply for Leave"})


# ---------------------------------------------------------------------
# Admin action — create a User login for a Teacher
# ---------------------------------------------------------------------

@login_required
def create_teacher_login(request, pk):
    from accounts.models import User
    if not (request.user.is_superuser or request.user.role == "admin"):
        return HttpResponseForbidden("Admin only.")
    teacher = get_object_or_404(Teacher, pk=pk)
    if request.method != "POST":
        return redirect("teacher_detail", pk=teacher.pk)

    username = (request.POST.get("username") or teacher.employee_no).strip()
    password = (request.POST.get("password") or teacher.employee_no).strip()

    if teacher.teacher_user_id:
        messages.info(request, "This teacher already has a login.")
        return redirect("teacher_edit", pk=teacher.pk)
    if User.objects.filter(username=username).exists():
        messages.error(request, f"Username '{username}' is already taken.")
        return redirect("teacher_edit", pk=teacher.pk)

    user = User.objects.create_user(
        username=username, password=password,
        first_name=teacher.first_name, last_name=teacher.last_name,
        role="teacher")
    teacher.teacher_user = user
    teacher.save(update_fields=["teacher_user"])
    messages.success(
        request,
        f"Teacher login created. Username: {username} · Password: {password}")
    return redirect("teacher_edit", pk=teacher.pk)


@login_required
def teacher_documents(request):
    """Teaching documents shared with the logged-in teacher.

    A document is visible if either:
      - it has NO subjects attached (= shared with all teachers), OR
      - at least one of its subjects is taught by this teacher.
    """
    teacher, redir = _gate(request)
    if redir:
        return redir
    my_subjects = teacher.subjects.all()
    # Docs with no subjects + docs whose subjects intersect mine
    from django.db.models import Q
    docs = (TeachingDocument.objects
            .filter(Q(subjects__isnull=True) | Q(subjects__in=my_subjects))
            .prefetch_related("subjects")
            .distinct())
    return render(request, "erp/teacher_documents.html", {
        "teacher": teacher, "rows": docs,
    })
