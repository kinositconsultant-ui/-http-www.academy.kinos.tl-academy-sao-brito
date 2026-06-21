"""HR module — dashboard + CRUD for recruitment, training, performance,
employee attendance and inventory.

All views require the user to be admin / HR. Simple list + add + delete
pattern (no edit — delete and re-add is fast enough for these volumes).
"""
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, Q
from django.http import HttpResponseForbidden, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404

from accounts.models import School
from .models import (
    Employee, LeaveRequest, SalaryPayment,
    JobPosting, Candidate, TrainingProgram, TrainingEnrollment,
    PerformanceReview, EmployeeAttendance,
    InventoryCategory, InventoryItem, InventoryAssignment,
)
from .forms import (
    JobPostingForm, CandidateForm, TrainingProgramForm, TrainingEnrollmentForm,
    PerformanceReviewForm, EmployeeAttendanceForm,
    InventoryCategoryForm, InventoryItemForm, InventoryAssignmentForm,
)


def _hr_required(view):
    """Decorator: only admin / superuser / hr role can access."""
    def wrapper(request, *args, **kwargs):
        u = request.user
        if not (u.is_authenticated and (u.is_superuser or u.role in ("admin", "hr"))):
            return HttpResponseForbidden("HR / Admin only.")
        return view(request, *args, **kwargs)
    return wrapper


# =====================================================================
# Dashboard
# =====================================================================

@login_required
@_hr_required
def hr_dashboard(request):
    today = date.today()
    month_start = today.replace(day=1)

    # Workforce
    employees = Employee.objects.all()
    active = employees.filter(is_active=True).count()
    inactive = employees.filter(is_active=False).count()
    on_leave_today = LeaveRequest.objects.filter(
        status="approved", start_date__lte=today, end_date__gte=today).count()

    # Payroll
    paid_this_month = SalaryPayment.objects.filter(
        status="paid", paid_date__gte=month_start, paid_date__lte=today
    ).aggregate(s=Sum("amount"))["s"] or Decimal("0")
    pending_payslips = SalaryPayment.objects.filter(status="pending").count()

    # Recruitment
    open_jobs = JobPosting.objects.filter(status="open").count()
    candidates_in_pipeline = Candidate.objects.exclude(
        stage__in=("hired", "rejected")).count()
    funnel = list(Candidate.objects.values("stage").annotate(c=Count("id")))
    stage_map = dict(Candidate.STAGE)
    funnel_chart = [{"label": stage_map.get(r["stage"], r["stage"]), "total": r["c"]}
                    for r in funnel]

    # Training
    active_trainings = TrainingProgram.objects.filter(
        status__in=("scheduled", "ongoing")).count()
    enrollments = TrainingEnrollment.objects.filter(status="enrolled").count()

    # Performance
    avg_rating = (PerformanceReview.objects.aggregate(a=Avg("rating"))["a"] or 0)
    reviews_this_quarter = PerformanceReview.objects.filter(
        period_end__gte=today.replace(month=((today.month - 1) // 3) * 3 + 1, day=1)
    ).count()

    # Today's employee attendance
    today_att = EmployeeAttendance.objects.filter(date=today)
    today_present = today_att.filter(status__in=("present", "remote", "late")).count()
    today_total = today_att.count()
    today_pct = round(100 * today_present / today_total, 1) if today_total else None

    # Inventory
    total_items = InventoryItem.objects.count()
    low_stock = [i for i in InventoryItem.objects.all() if i.is_low_stock]
    inventory_value = sum((i.total_value for i in InventoryItem.objects.all()), 0)
    items_assigned = InventoryAssignment.objects.filter(status="assigned").count()

    return render(request, "erp/hr/dashboard.html", {
        "school": School.get_active(),
        # Workforce
        "active": active, "inactive": inactive, "on_leave_today": on_leave_today,
        "total_employees": active + inactive,
        # Payroll
        "paid_this_month": paid_this_month, "pending_payslips": pending_payslips,
        # Recruitment
        "open_jobs": open_jobs, "candidates_in_pipeline": candidates_in_pipeline,
        "funnel_chart": funnel_chart,
        # Training
        "active_trainings": active_trainings, "enrollments": enrollments,
        # Performance
        "avg_rating": round(float(avg_rating), 2),
        "reviews_this_quarter": reviews_this_quarter,
        # Attendance
        "today_present": today_present, "today_total": today_total,
        "today_pct": today_pct,
        # Inventory
        "total_items": total_items, "low_stock_count": len(low_stock),
        "low_stock_items": low_stock[:5],
        "inventory_value": inventory_value, "items_assigned": items_assigned,
    })


# =====================================================================
# Generic helpers
# =====================================================================

def _crud_list(request, model, template, ctx_extra=None):
    qs = model.objects.all()
    ctx = {"rows": qs}
    if ctx_extra:
        ctx.update(ctx_extra)
    return render(request, template, ctx)


def _crud_add(request, form_class, redirect_to, title):
    if request.method == "POST":
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, f"{title} saved.")
            return redirect(redirect_to)
    else:
        form = form_class()
    return render(request, "erp/form.html", {"form": form, "title": f"Add {title}"})


def _crud_delete(request, obj, redirect_to, label):
    if request.method == "POST":
        obj.delete()
        messages.success(request, f"{label} deleted.")
        return redirect(redirect_to)
    return render(request, "erp/confirm_delete.html", {"object": obj, "type": label})


# =====================================================================
# Recruitment
# =====================================================================

@login_required
@_hr_required
def job_list(request):
    return _crud_list(request, JobPosting, "erp/hr/job_list.html")


@login_required
@_hr_required
def job_add(request):
    return _crud_add(request, JobPostingForm, "hr_job_list", "Job Posting")


@login_required
@_hr_required
def job_delete(request, pk):
    return _crud_delete(request, get_object_or_404(JobPosting, pk=pk),
                        "hr_job_list", "Job posting")


@login_required
@_hr_required
def candidate_list(request):
    return _crud_list(request, Candidate, "erp/hr/candidate_list.html")


@login_required
@_hr_required
def candidate_add(request):
    return _crud_add(request, CandidateForm, "hr_candidate_list", "Candidate")


@login_required
@_hr_required
def candidate_delete(request, pk):
    return _crud_delete(request, get_object_or_404(Candidate, pk=pk),
                        "hr_candidate_list", "Candidate")


# =====================================================================
# Training
# =====================================================================

@login_required
@_hr_required
def training_list(request):
    return _crud_list(request, TrainingProgram, "erp/hr/training_list.html")


@login_required
@_hr_required
def training_add(request):
    return _crud_add(request, TrainingProgramForm, "hr_training_list", "Training")


@login_required
@_hr_required
def training_delete(request, pk):
    return _crud_delete(request, get_object_or_404(TrainingProgram, pk=pk),
                        "hr_training_list", "Training")


@login_required
@_hr_required
def enrollment_list(request):
    return _crud_list(request, TrainingEnrollment, "erp/hr/enrollment_list.html")


@login_required
@_hr_required
def enrollment_add(request):
    return _crud_add(request, TrainingEnrollmentForm, "hr_enrollment_list", "Enrollment")


@login_required
@_hr_required
def enrollment_delete(request, pk):
    return _crud_delete(request, get_object_or_404(TrainingEnrollment, pk=pk),
                        "hr_enrollment_list", "Enrollment")


# =====================================================================
# Performance
# =====================================================================

@login_required
@_hr_required
def review_list(request):
    return _crud_list(request, PerformanceReview, "erp/hr/review_list.html")


@login_required
@_hr_required
def review_add(request):
    if request.method == "POST":
        form = PerformanceReviewForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.reviewer = request.user
            obj.save()
            messages.success(request, "Performance review saved.")
            return redirect("hr_review_list")
    else:
        form = PerformanceReviewForm()
    return render(request, "erp/form.html",
                  {"form": form, "title": "Add Performance Review"})


@login_required
@_hr_required
def review_delete(request, pk):
    return _crud_delete(request, get_object_or_404(PerformanceReview, pk=pk),
                        "hr_review_list", "Performance review")


# =====================================================================
# Employee attendance
# =====================================================================

@login_required
@_hr_required
def employee_attendance_list(request):
    qs = EmployeeAttendance.objects.select_related("employee")
    return render(request, "erp/hr/employee_attendance_list.html", {"rows": qs})


@login_required
@_hr_required
def employee_attendance_add(request):
    return _crud_add(request, EmployeeAttendanceForm,
                     "hr_employee_attendance_list", "Attendance entry")


@login_required
@_hr_required
def employee_attendance_delete(request, pk):
    return _crud_delete(request, get_object_or_404(EmployeeAttendance, pk=pk),
                        "hr_employee_attendance_list", "Attendance entry")


# =====================================================================
# Inventory
# =====================================================================

@login_required
@_hr_required
def inventory_list(request):
    items = InventoryItem.objects.select_related("category").all()
    return render(request, "erp/hr/inventory_list.html", {"rows": items})


@login_required
@_hr_required
def inventory_add(request):
    return _crud_add(request, InventoryItemForm, "hr_inventory_list", "Inventory item")


@login_required
@_hr_required
def inventory_delete(request, pk):
    return _crud_delete(request, get_object_or_404(InventoryItem, pk=pk),
                        "hr_inventory_list", "Inventory item")


@login_required
@_hr_required
def category_add(request):
    return _crud_add(request, InventoryCategoryForm, "hr_inventory_list",
                     "Inventory category")


@login_required
@_hr_required
def assignment_list(request):
    rows = InventoryAssignment.objects.select_related("item", "employee").all()
    return render(request, "erp/hr/assignment_list.html", {"rows": rows})


@login_required
@_hr_required
def assignment_add(request):
    if request.method == "POST":
        form = InventoryAssignmentForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            # Auto-decrement stock if newly assigned
            if obj.status == "assigned" and obj.item.quantity >= obj.quantity:
                obj.item.quantity -= obj.quantity
                obj.item.save(update_fields=["quantity"])
            obj.save()
            messages.success(request, "Assignment recorded.")
            return redirect("hr_assignment_list")
    else:
        form = InventoryAssignmentForm()
    return render(request, "erp/form.html",
                  {"form": form, "title": "Assign Inventory Item"})


@login_required
@_hr_required
def assignment_delete(request, pk):
    return _crud_delete(request, get_object_or_404(InventoryAssignment, pk=pk),
                        "hr_assignment_list", "Assignment")


# =====================================================================
# Payslip PDF (one per SalaryPayment row)
# =====================================================================

@login_required
@_hr_required
def payslip_pdf(request, pk):
    from .payslip_pdf import build_payslip_pdf
    payslip = get_object_or_404(SalaryPayment, pk=pk)
    pdf = build_payslip_pdf(payslip, School.get_active())
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = (
        f'attachment; filename="payslip_{payslip.teacher.full_name.replace(" ", "_")}'
        f'_{payslip.month.replace(" ", "_")}.pdf"')
    return resp
