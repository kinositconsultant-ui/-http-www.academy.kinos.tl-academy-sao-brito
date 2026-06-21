"""Student self-service portal — read-only access to grades, attendance,
remaining (failed) subjects, fee invoices, academic credits and credit notes.
"""
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden
from django.db.models import Sum

from accounts.models import School
from .models import (
    Student, Grade, AcademicYear, FeeInvoice, CreditNote, Subject,
)
from .report_card import build_report_card


def _student_only(user):
    return user.is_authenticated and (user.role == "student" or user.is_superuser)


def _get_my_student(user):
    """Return the Student row linked to the logged-in user, or None."""
    return Student.objects.filter(student_user=user).select_related("school_class").first()


def _overall_stats(student, year=None):
    """Compute overall % avg + pass/fail counts (optionally filtered by year)."""
    qs = student.grades.all()
    if year:
        qs = qs.filter(academic_year=year)
    grades = list(qs)
    if not grades:
        return {"avg": 0, "passed": 0, "failed": 0, "total": 0}
    total = len(grades)
    passed = sum(1 for g in grades if g.is_pass)
    return {
        "avg": round(sum(g.percentage for g in grades) / total, 2),
        "passed": passed,
        "failed": total - passed,
        "total": total,
    }


def _attendance_rate(student, year=None):
    qs = student.attendance.all()
    if year:
        qs = qs.filter(date__gte=year.start_date, date__lte=year.end_date)
    total = qs.count()
    if not total:
        return None
    present = qs.filter(status="present").count()
    return round(100 * present / total, 1)


def _subjects_to_repeat(student):
    """Subjects the student has failed at least once and has not yet passed.

    For each (subject) where any grade is_pass=False AND no later grade is
    is_pass=True, mark it as 'to repeat'.
    """
    grades = list(student.grades.select_related("subject", "academic_year")
                  .order_by("subject_id", "recorded_at"))
    by_subject = defaultdict(list)
    for g in grades:
        by_subject[g.subject_id].append(g)

    rows = []
    for sid, gs in by_subject.items():
        # Has the student ever passed this subject?
        passed_any = any(g.is_pass for g in gs)
        failed_any = any(not g.is_pass for g in gs)
        if failed_any and not passed_any:
            last_fail = max((g for g in gs if not g.is_pass),
                            key=lambda g: g.recorded_at)
            rows.append({
                "subject": last_fail.subject,
                "last_year": last_fail.academic_year,
                "last_semester": last_fail.get_semester_display(),
                "last_score": last_fail.percentage,
                "attempts": len(gs),
            })
    rows.sort(key=lambda r: r["subject"].name)
    return rows


@login_required
def student_dashboard(request):
    if not _student_only(request.user):
        return redirect("/api/post-login/")
    student = _get_my_student(request.user)
    if not student:
        return render(request, "erp/student_no_link.html", {})

    current_year = AcademicYear.objects.filter(is_current=True).first()
    overall = _overall_stats(student)
    current = _overall_stats(student, current_year) if current_year else overall
    att_rate = _attendance_rate(student, current_year)
    invoices = student.invoices.all().order_by("-issued_date")[:5]
    outstanding = student.invoices.exclude(status="paid").aggregate(
        a=Sum("amount"), p=Sum("amount_paid"))
    balance = (outstanding["a"] or 0) - (outstanding["p"] or 0)
    to_repeat = _subjects_to_repeat(student)
    # Earned credit = 1 per distinct passed subject (latest attempt is pass)
    credits_earned = len({g.subject_id for g in student.grades.all() if g.is_pass})
    credit_notes = student.credit_notes.all()[:5]
    from .academy_views import today_widget_context
    return render(request, "erp/student_dashboard.html", {
        "student": student,
        "school": School.get_active(),
        "current_year": current_year,
        "overall": overall,
        "current": current,
        "attendance_rate": att_rate,
        "invoices": invoices,
        "balance": balance,
        "to_repeat": to_repeat,
        "credits_earned": credits_earned,
        "credit_notes": credit_notes,
        **today_widget_context(request.user),
    })


@login_required
def student_grades(request):
    if not _student_only(request.user):
        return redirect("/api/post-login/")
    student = _get_my_student(request.user)
    if not student:
        return render(request, "erp/student_no_link.html", {})
    year_id = request.GET.get("year")
    years = AcademicYear.objects.all()
    selected = AcademicYear.objects.filter(id=year_id).first() if year_id else (
        AcademicYear.objects.filter(is_current=True).first())
    grades = student.grades.select_related("subject", "academic_year")
    if selected:
        grades = grades.filter(academic_year=selected)
    grades = list(grades.order_by("semester", "subject__name"))
    # Group by semester
    by_sem = defaultdict(list)
    for g in grades:
        by_sem[g.get_semester_display()].append(g)
    return render(request, "erp/student_grades.html", {
        "student": student, "years": years,
        "selected_year": selected, "by_sem": dict(by_sem),
        "overall": _overall_stats(student, selected),
    })


@login_required
def student_subjects(request):
    """Subjects student must repeat (failed) + all subjects assigned to class."""
    if not _student_only(request.user):
        return redirect("/api/post-login/")
    student = _get_my_student(request.user)
    if not student:
        return render(request, "erp/student_no_link.html", {})
    to_repeat = _subjects_to_repeat(student)
    class_subjects = []
    if student.school_class:
        class_subjects = list(
            Subject.objects.filter(school_class=student.school_class).order_by("name"))
    return render(request, "erp/student_subjects.html", {
        "student": student, "to_repeat": to_repeat,
        "class_subjects": class_subjects,
    })


@login_required
def student_credits(request):
    """Academic credits earned + finance credit notes."""
    if not _student_only(request.user):
        return redirect("/api/post-login/")
    student = _get_my_student(request.user)
    if not student:
        return render(request, "erp/student_no_link.html", {})
    # Academic credits: 1 credit per distinct subject the student has passed
    passed_subject_ids = {g.subject_id for g in student.grades.all() if g.is_pass}
    passed_subjects = list(
        Subject.objects.filter(id__in=passed_subject_ids).order_by("name"))
    credit_notes = list(student.credit_notes.select_related("invoice"))
    total_credit_amount = sum(c.amount for c in credit_notes if c.status == "open")
    return render(request, "erp/student_credits.html", {
        "student": student,
        "school": School.get_active(),
        "passed_subjects": passed_subjects,
        "credits_earned": len(passed_subjects),
        "credit_notes": credit_notes,
        "total_credit_amount": total_credit_amount,
    })


@login_required
def student_invoices(request):
    """Read-only fee invoices for the logged-in student."""
    if not _student_only(request.user):
        return redirect("/api/post-login/")
    student = _get_my_student(request.user)
    if not student:
        return render(request, "erp/student_no_link.html", {})
    invoices = student.invoices.all().order_by("-issued_date")
    return render(request, "erp/student_invoices.html", {
        "student": student, "invoices": invoices,
        "school": School.get_active(),
    })


@login_required
def student_report_card(request):
    """Download own report card PDF."""
    if not _student_only(request.user):
        return redirect("/api/post-login/")
    student = _get_my_student(request.user)
    if not student:
        return HttpResponseForbidden("No student profile linked.")
    year_id = request.GET.get("year")
    year = AcademicYear.objects.filter(id=year_id).first() if year_id else (
        AcademicYear.objects.filter(is_current=True).first())
    grades_qs = student.grades.select_related("subject", "academic_year")
    if year:
        grades_qs = grades_qs.filter(academic_year=year)
    grades = list(grades_qs.order_by("subject__name", "semester"))
    att = student.attendance.all()
    if year:
        att = att.filter(date__gte=year.start_date, date__lte=year.end_date)
    stats = {"present": att.filter(status="present").count(), "total": att.count()}
    pdf = build_report_card(
        student=student, grades=grades,
        school=School.get_active(), academic_year=year, attendance_stats=stats)
    safe = student.full_name.replace(" ", "_")
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = (
        f'attachment; filename="report-card_{safe}_{(year.name if year else "all")}.pdf"')
    return resp


# =====================================================================
# Admin action — create a User login for a Student
# =====================================================================

@login_required
def create_student_login(request, pk):
    """Admin-only: create (or relink) a User account for the student.

    Username defaults to the student's admission number; password defaults to
    the same admission number (the student should change it after first login).
    """
    from django.contrib import messages
    from accounts.models import User
    if not (request.user.is_superuser or request.user.role == "admin"):
        return HttpResponseForbidden("Admin only.")
    student = get_object_or_404(Student, pk=pk)
    if request.method != "POST":
        return redirect("student_detail", pk=student.pk)

    username = (request.POST.get("username") or student.admission_no).strip()
    password = (request.POST.get("password") or student.admission_no).strip()

    if student.student_user_id:
        messages.info(request, "This student already has a login.")
        return redirect("student_detail", pk=student.pk)

    if User.objects.filter(username=username).exists():
        messages.error(request, f"Username '{username}' is already taken.")
        return redirect("student_detail", pk=student.pk)

    user = User.objects.create_user(
        username=username, password=password,
        first_name=student.first_name, last_name=student.last_name,
        role="student",
    )
    student.student_user = user
    student.save(update_fields=["student_user"])
    messages.success(
        request,
        f"Student login created. Username: {username} · Password: {password}")
    return redirect("student_detail", pk=student.pk)


# =====================================================================
# Admin CRUD — Credit Notes
# =====================================================================

@login_required
def credit_note_list(request):
    if not (request.user.is_superuser or request.user.role in ("admin", "accountant")):
        return HttpResponseForbidden("Not allowed.")
    notes = CreditNote.objects.select_related("student", "invoice").all()
    return render(request, "erp/credit_note_list.html", {"notes": notes})


@login_required
def credit_note_create(request):
    from django.contrib import messages
    from .forms import CreditNoteForm
    if not (request.user.is_superuser or request.user.role in ("admin", "accountant")):
        return HttpResponseForbidden("Not allowed.")
    if request.method == "POST":
        form = CreditNoteForm(request.POST)
        if form.is_valid():
            cn = form.save(commit=False)
            cn.issued_by = request.user
            cn.save()
            # If linked to an invoice & status "applied", reduce the invoice balance.
            if cn.invoice and cn.status == "applied":
                inv = cn.invoice
                inv.amount = max(0, float(inv.amount) - float(cn.amount))
                inv.refresh_status()
                inv.save()
            messages.success(request, "Credit note created.")
            return redirect("credit_note_list")
    else:
        form = CreditNoteForm()
    return render(request, "erp/form.html", {"form": form, "title": "Add Credit Note"})


@login_required
def credit_note_delete(request, pk):
    from django.contrib import messages
    if not (request.user.is_superuser or request.user.role in ("admin", "accountant")):
        return HttpResponseForbidden("Not allowed.")
    cn = get_object_or_404(CreditNote, pk=pk)
    if request.method == "POST":
        cn.delete()
        messages.success(request, "Credit note deleted.")
        return redirect("credit_note_list")
    return render(request, "erp/confirm_delete.html", {"object": cn, "type": "credit note"})
