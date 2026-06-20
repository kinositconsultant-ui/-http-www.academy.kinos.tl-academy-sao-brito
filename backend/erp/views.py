from decimal import Decimal
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import HttpResponse

from .models import (
    SchoolClass, Subject, Student, Teacher, Attendance, Grade,
    FeeStructure, FeeInvoice, FeePayment, SalaryPayment, Expense, Income,
    Donor, Donation, Employee, LeaveRequest, AcademicYear,
)
from .forms import (
    SchoolClassForm, SubjectForm, StudentForm, TeacherForm, AttendanceForm, GradeForm,
    FeeStructureForm, FeeInvoiceForm, FeePaymentForm, SalaryPaymentForm,
    ExpenseForm, IncomeForm, DonorForm, DonationForm, EmployeeForm, LeaveRequestForm,
    AcademicYearForm,
)


# ---------- Helpers ----------

def _crud_list(request, model, template, extra=None):
    objs = model.objects.all()
    ctx = {"objects": objs}
    if extra:
        ctx.update(extra)
    return render(request, template, ctx)


def _save_form(request, form_cls, instance, redirect_to, success_msg, template, title, extra=None):
    if request.method == "POST":
        form = form_cls(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, success_msg)
            return redirect(redirect_to)
    else:
        form = form_cls(instance=instance)
    ctx = {"form": form, "title": title}
    if extra:
        ctx.update(extra)
    return render(request, template, ctx)


# ---------- Dashboard ----------

@login_required
def dashboard(request):
    today = timezone.now().date()
    month_start = today.replace(day=1)

    total_students = Student.objects.filter(is_active=True).count()
    total_teachers = Teacher.objects.filter(is_active=True).count()
    total_employees = Employee.objects.filter(is_active=True).count()
    total_classes = SchoolClass.objects.count()

    fees_collected_month = FeePayment.objects.filter(paid_on__gte=month_start).aggregate(
        s=Sum("amount"))["s"] or 0
    outstanding = FeeInvoice.objects.exclude(status="paid").aggregate(
        s=Sum("amount"))["s"] or 0
    outstanding_paid = FeeInvoice.objects.exclude(status="paid").aggregate(
        s=Sum("amount_paid"))["s"] or 0
    outstanding_balance = (outstanding or 0) - (outstanding_paid or 0)

    expenses_month = Expense.objects.filter(date__gte=month_start).aggregate(
        s=Sum("amount"))["s"] or 0
    donations_month = Donation.objects.filter(date__gte=month_start).aggregate(
        s=Sum("amount"))["s"] or 0
    salary_pending = SalaryPayment.objects.filter(status="pending").aggregate(
        s=Sum("amount"))["s"] or 0

    pending_leaves = LeaveRequest.objects.filter(status="pending").count()

    recent_payments = FeePayment.objects.select_related("invoice__student").order_by("-paid_on")[:6]
    recent_expenses = Expense.objects.order_by("-date")[:6]
    recent_donations = Donation.objects.select_related("donor").order_by("-date")[:6]

    return render(request, "erp/dashboard.html", {
        "kpis": {
            "students": total_students,
            "teachers": total_teachers,
            "employees": total_employees,
            "classes": total_classes,
            "fees_collected_month": fees_collected_month,
            "outstanding_balance": outstanding_balance,
            "expenses_month": expenses_month,
            "donations_month": donations_month,
            "salary_pending": salary_pending,
            "pending_leaves": pending_leaves,
        },
        "recent_payments": recent_payments,
        "recent_expenses": recent_expenses,
        "recent_donations": recent_donations,
    })


# ---------- Academic Years ----------

@login_required
def academic_year_list(request):
    return _crud_list(request, AcademicYear, "erp/academic_year_list.html")

@login_required
def academic_year_create(request):
    return _save_form(request, AcademicYearForm, None, "academic_year_list",
                      "Academic year created.", "erp/form.html", "Add Academic Year")

@login_required
def academic_year_edit(request, pk):
    obj = get_object_or_404(AcademicYear, pk=pk)
    return _save_form(request, AcademicYearForm, obj, "academic_year_list",
                      "Academic year updated.", "erp/form.html", "Edit Academic Year")

@login_required
def academic_year_delete(request, pk):
    obj = get_object_or_404(AcademicYear, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Academic year deleted.")
        return redirect("academic_year_list")
    return render(request, "erp/confirm_delete.html", {"object": obj, "back": "academic_year_list"})


# ---------- Classes ----------

@login_required
def class_list(request):
    return _crud_list(request, SchoolClass, "erp/class_list.html")

@login_required
def class_create(request):
    return _save_form(request, SchoolClassForm, None, "class_list",
                      "Class created.", "erp/form.html", "Add Class")

@login_required
def class_edit(request, pk):
    obj = get_object_or_404(SchoolClass, pk=pk)
    return _save_form(request, SchoolClassForm, obj, "class_list",
                      "Class updated.", "erp/form.html", "Edit Class")

@login_required
def class_delete(request, pk):
    obj = get_object_or_404(SchoolClass, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Class deleted.")
        return redirect("class_list")
    return render(request, "erp/confirm_delete.html", {"object": obj, "back": "class_list"})


# ---------- Subjects ----------

@login_required
def subject_list(request):
    return _crud_list(request, Subject, "erp/subject_list.html")

@login_required
def subject_create(request):
    return _save_form(request, SubjectForm, None, "subject_list",
                      "Subject created.", "erp/form.html", "Add Subject")

@login_required
def subject_edit(request, pk):
    obj = get_object_or_404(Subject, pk=pk)
    return _save_form(request, SubjectForm, obj, "subject_list",
                      "Subject updated.", "erp/form.html", "Edit Subject")

@login_required
def subject_delete(request, pk):
    obj = get_object_or_404(Subject, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Subject deleted.")
        return redirect("subject_list")
    return render(request, "erp/confirm_delete.html", {"object": obj, "back": "subject_list"})


# ---------- Students ----------

@login_required
def student_list(request):
    q = request.GET.get("q", "")
    qs = Student.objects.select_related("school_class").all()
    if q:
        qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) |
                       Q(admission_no__icontains=q))
    return render(request, "erp/student_list.html", {"objects": qs, "q": q})

@login_required
def student_create(request):
    return _save_form(request, StudentForm, None, "student_list",
                      "Student admitted.", "erp/form.html", "Admit New Student")

@login_required
def student_edit(request, pk):
    obj = get_object_or_404(Student, pk=pk)
    return _save_form(request, StudentForm, obj, "student_list",
                      "Student updated.", "erp/form.html", "Edit Student")

@login_required
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    invoices = student.invoices.all()
    grades = student.grades.select_related("subject")
    attendance = student.attendance.all()[:30]
    return render(request, "erp/student_detail.html", {
        "student": student, "invoices": invoices,
        "grades": grades, "attendance": attendance,
    })

@login_required
def student_delete(request, pk):
    obj = get_object_or_404(Student, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Student deleted.")
        return redirect("student_list")
    return render(request, "erp/confirm_delete.html", {"object": obj, "back": "student_list"})


# ---------- Teachers ----------

@login_required
def teacher_list(request):
    return render(request, "erp/teacher_list.html",
                  {"objects": Teacher.objects.prefetch_related("subjects").all()})

@login_required
def teacher_create(request):
    return _save_form(request, TeacherForm, None, "teacher_list",
                      "Teacher added.", "erp/form.html", "Add Teacher")

@login_required
def teacher_edit(request, pk):
    obj = get_object_or_404(Teacher, pk=pk)
    return _save_form(request, TeacherForm, obj, "teacher_list",
                      "Teacher updated.", "erp/form.html", "Edit Teacher")

@login_required
def teacher_delete(request, pk):
    obj = get_object_or_404(Teacher, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Teacher deleted.")
        return redirect("teacher_list")
    return render(request, "erp/confirm_delete.html", {"object": obj, "back": "teacher_list"})


# ---------- Attendance ----------

@login_required
def attendance_list(request):
    qs = Attendance.objects.select_related("student").order_by("-date")[:200]
    return render(request, "erp/attendance_list.html", {"objects": qs})

@login_required
def attendance_create(request):
    return _save_form(request, AttendanceForm, None, "attendance_list",
                      "Attendance recorded.", "erp/form.html", "Mark Attendance")

@login_required
def attendance_edit(request, pk):
    obj = get_object_or_404(Attendance, pk=pk)
    return _save_form(request, AttendanceForm, obj, "attendance_list",
                      "Attendance updated.", "erp/form.html", "Edit Attendance")

@login_required
def attendance_delete(request, pk):
    obj = get_object_or_404(Attendance, pk=pk)
    if request.method == "POST":
        obj.delete()
        return redirect("attendance_list")
    return render(request, "erp/confirm_delete.html", {"object": obj, "back": "attendance_list"})


# ---------- Grades ----------

@login_required
def grade_list(request):
    qs = Grade.objects.select_related("student", "subject").order_by("-recorded_at")[:200]
    return render(request, "erp/grade_list.html", {"objects": qs})

@login_required
def grade_create(request):
    return _save_form(request, GradeForm, None, "grade_list",
                      "Grade recorded.", "erp/form.html", "Record Grade")

@login_required
def grade_edit(request, pk):
    obj = get_object_or_404(Grade, pk=pk)
    return _save_form(request, GradeForm, obj, "grade_list",
                      "Grade updated.", "erp/form.html", "Edit Grade")

@login_required
def grade_delete(request, pk):
    obj = get_object_or_404(Grade, pk=pk)
    if request.method == "POST":
        obj.delete()
        return redirect("grade_list")
    return render(request, "erp/confirm_delete.html", {"object": obj, "back": "grade_list"})


# ---------- Fee Structures ----------

@login_required
def fee_structure_list(request):
    return _crud_list(request, FeeStructure, "erp/fee_structure_list.html")

@login_required
def fee_structure_create(request):
    return _save_form(request, FeeStructureForm, None, "fee_structure_list",
                      "Fee structure created.", "erp/form.html", "Add Fee Structure")

@login_required
def fee_structure_edit(request, pk):
    obj = get_object_or_404(FeeStructure, pk=pk)
    return _save_form(request, FeeStructureForm, obj, "fee_structure_list",
                      "Fee structure updated.", "erp/form.html", "Edit Fee Structure")

@login_required
def fee_structure_delete(request, pk):
    obj = get_object_or_404(FeeStructure, pk=pk)
    if request.method == "POST":
        obj.delete()
        return redirect("fee_structure_list")
    return render(request, "erp/confirm_delete.html", {"object": obj, "back": "fee_structure_list"})


# ---------- Fee Invoices ----------

@login_required
def invoice_list(request):
    status = request.GET.get("status", "")
    qs = FeeInvoice.objects.select_related("student")
    if status:
        qs = qs.filter(status=status)
    for inv in qs:
        # refresh overdue status on view
        if inv.status not in ("paid",):
            inv.refresh_status()
    return render(request, "erp/invoice_list.html", {"objects": qs, "status": status})

@login_required
def invoice_create(request):
    return _save_form(request, FeeInvoiceForm, None, "invoice_list",
                      "Invoice created.", "erp/form.html", "Create Invoice")

@login_required
def invoice_edit(request, pk):
    obj = get_object_or_404(FeeInvoice, pk=pk)
    return _save_form(request, FeeInvoiceForm, obj, "invoice_list",
                      "Invoice updated.", "erp/form.html", "Edit Invoice")

@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(FeeInvoice, pk=pk)
    payments = invoice.payments.all()
    if request.method == "POST":
        form = FeePaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.received_by = request.user
            payment.save()
            invoice.amount_paid = invoice.payments.aggregate(s=Sum("amount"))["s"] or 0
            invoice.refresh_status()
            invoice.save()
            # Mirror to income ledger
            Income.objects.create(
                title=f"Fee payment - {invoice.student.full_name}",
                source="fees", amount=payment.amount, date=payment.paid_on,
                note=f"Invoice #{invoice.id}: {invoice.title}",
            )
            messages.success(request, "Payment recorded.")
            return redirect("invoice_detail", pk=invoice.pk)
        else:
            messages.error(request, f"Could not record payment: {form.errors.as_text()}")
    else:
        form = FeePaymentForm(initial={"paid_on": timezone.now().date()})
    return render(request, "erp/invoice_detail.html",
                  {"invoice": invoice, "payments": payments, "form": form})

@login_required
def invoice_delete(request, pk):
    obj = get_object_or_404(FeeInvoice, pk=pk)
    if request.method == "POST":
        obj.delete()
        return redirect("invoice_list")
    return render(request, "erp/confirm_delete.html", {"object": obj, "back": "invoice_list"})


# ---------- Salaries ----------

@login_required
def salary_list(request):
    qs = SalaryPayment.objects.select_related("teacher").all()
    return render(request, "erp/salary_list.html", {"objects": qs})

@login_required
def salary_create(request):
    return _save_form(request, SalaryPaymentForm, None, "salary_list",
                      "Salary record created.", "erp/form.html", "Add Salary Payment")

@login_required
def salary_edit(request, pk):
    obj = get_object_or_404(SalaryPayment, pk=pk)
    return _save_form(request, SalaryPaymentForm, obj, "salary_list",
                      "Salary record updated.", "erp/form.html", "Edit Salary Payment")

@login_required
def salary_pay(request, pk):
    obj = get_object_or_404(SalaryPayment, pk=pk)
    if request.method == "POST":
        obj.status = "paid"
        obj.paid_date = timezone.now().date()
        obj.save()
        Expense.objects.create(
            title=f"Salary - {obj.teacher.full_name} ({obj.month})",
            category="other", amount=obj.net, paid_to=obj.teacher.full_name,
            date=obj.paid_date, note="Auto-recorded from salary payment.",
            recorded_by=request.user,
        )
        messages.success(request, "Marked as paid and recorded as expense.")
    return redirect("salary_list")

@login_required
def salary_delete(request, pk):
    obj = get_object_or_404(SalaryPayment, pk=pk)
    if request.method == "POST":
        obj.delete()
        return redirect("salary_list")
    return render(request, "erp/confirm_delete.html", {"object": obj, "back": "salary_list"})


# ---------- Expenses ----------

@login_required
def expense_list(request):
    return render(request, "erp/expense_list.html",
                  {"objects": Expense.objects.all(),
                   "total": Expense.objects.aggregate(s=Sum("amount"))["s"] or 0})

@login_required
def expense_create(request):
    if request.method == "POST":
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.recorded_by = request.user
            obj.save()
            messages.success(request, "Expense recorded.")
            return redirect("expense_list")
    else:
        form = ExpenseForm()
    return render(request, "erp/form.html", {"form": form, "title": "Record Expense"})

@login_required
def expense_edit(request, pk):
    obj = get_object_or_404(Expense, pk=pk)
    return _save_form(request, ExpenseForm, obj, "expense_list",
                      "Expense updated.", "erp/form.html", "Edit Expense")

@login_required
def expense_delete(request, pk):
    obj = get_object_or_404(Expense, pk=pk)
    if request.method == "POST":
        obj.delete()
        return redirect("expense_list")
    return render(request, "erp/confirm_delete.html", {"object": obj, "back": "expense_list"})


# ---------- Incomes ----------

@login_required
def income_list(request):
    return render(request, "erp/income_list.html",
                  {"objects": Income.objects.all(),
                   "total": Income.objects.aggregate(s=Sum("amount"))["s"] or 0})

@login_required
def income_create(request):
    return _save_form(request, IncomeForm, None, "income_list",
                      "Income recorded.", "erp/form.html", "Record Income")

@login_required
def income_edit(request, pk):
    obj = get_object_or_404(Income, pk=pk)
    return _save_form(request, IncomeForm, obj, "income_list",
                      "Income updated.", "erp/form.html", "Edit Income")

@login_required
def income_delete(request, pk):
    obj = get_object_or_404(Income, pk=pk)
    if request.method == "POST":
        obj.delete()
        return redirect("income_list")
    return render(request, "erp/confirm_delete.html", {"object": obj, "back": "income_list"})


# ---------- Donors / Donations ----------

@login_required
def donor_list(request):
    qs = Donor.objects.prefetch_related("donations").all()
    return render(request, "erp/donor_list.html", {"objects": qs})

@login_required
def donor_create(request):
    return _save_form(request, DonorForm, None, "donor_list",
                      "Donor added.", "erp/form.html", "Add Donor")

@login_required
def donor_edit(request, pk):
    obj = get_object_or_404(Donor, pk=pk)
    return _save_form(request, DonorForm, obj, "donor_list",
                      "Donor updated.", "erp/form.html", "Edit Donor")

@login_required
def donor_detail(request, pk):
    donor = get_object_or_404(Donor, pk=pk)
    return render(request, "erp/donor_detail.html", {"donor": donor})

@login_required
def donor_delete(request, pk):
    obj = get_object_or_404(Donor, pk=pk)
    if request.method == "POST":
        obj.delete()
        return redirect("donor_list")
    return render(request, "erp/confirm_delete.html", {"object": obj, "back": "donor_list"})


@login_required
def donation_list(request):
    return render(request, "erp/donation_list.html",
                  {"objects": Donation.objects.select_related("donor").all(),
                   "total": Donation.objects.aggregate(s=Sum("amount"))["s"] or 0})

@login_required
def donation_create(request):
    if request.method == "POST":
        form = DonationForm(request.POST)
        if form.is_valid():
            donation = form.save()
            Income.objects.create(
                title=f"Donation - {donation.donor.name}",
                source="donation", amount=donation.amount, date=donation.date,
                note=f"Purpose: {donation.get_purpose_display()}",
            )
            messages.success(request, "Donation recorded.")
            return redirect("donation_list")
    else:
        form = DonationForm(initial={"date": timezone.now().date()})
    return render(request, "erp/form.html", {"form": form, "title": "Record Donation"})

@login_required
def donation_edit(request, pk):
    obj = get_object_or_404(Donation, pk=pk)
    return _save_form(request, DonationForm, obj, "donation_list",
                      "Donation updated.", "erp/form.html", "Edit Donation")

@login_required
def donation_delete(request, pk):
    obj = get_object_or_404(Donation, pk=pk)
    if request.method == "POST":
        obj.delete()
        return redirect("donation_list")
    return render(request, "erp/confirm_delete.html", {"object": obj, "back": "donation_list"})


# ---------- HR ----------

@login_required
def employee_list(request):
    return render(request, "erp/employee_list.html", {"objects": Employee.objects.all()})

@login_required
def employee_create(request):
    return _save_form(request, EmployeeForm, None, "employee_list",
                      "Employee added.", "erp/form.html", "Add Employee")

@login_required
def employee_edit(request, pk):
    obj = get_object_or_404(Employee, pk=pk)
    return _save_form(request, EmployeeForm, obj, "employee_list",
                      "Employee updated.", "erp/form.html", "Edit Employee")

@login_required
def employee_delete(request, pk):
    obj = get_object_or_404(Employee, pk=pk)
    if request.method == "POST":
        obj.delete()
        return redirect("employee_list")
    return render(request, "erp/confirm_delete.html", {"object": obj, "back": "employee_list"})


@login_required
def leave_list(request):
    return render(request, "erp/leave_list.html",
                  {"objects": LeaveRequest.objects.select_related("employee").all()})

@login_required
def leave_create(request):
    return _save_form(request, LeaveRequestForm, None, "leave_list",
                      "Leave request submitted.", "erp/form.html", "Submit Leave Request")

@login_required
def leave_edit(request, pk):
    obj = get_object_or_404(LeaveRequest, pk=pk)
    return _save_form(request, LeaveRequestForm, obj, "leave_list",
                      "Leave updated.", "erp/form.html", "Edit Leave Request")

@login_required
def leave_decide(request, pk, decision):
    obj = get_object_or_404(LeaveRequest, pk=pk)
    if decision in ("approved", "rejected"):
        obj.status = decision
        obj.decided_by = request.user
        obj.decided_at = timezone.now()
        obj.save()
        messages.success(request, f"Leave {decision}.")
    return redirect("leave_list")

@login_required
def leave_delete(request, pk):
    obj = get_object_or_404(LeaveRequest, pk=pk)
    if request.method == "POST":
        obj.delete()
        return redirect("leave_list")
    return render(request, "erp/confirm_delete.html", {"object": obj, "back": "leave_list"})


# ---------- Reports ----------

@login_required
def finance_report(request):
    today = timezone.now().date()
    year_start = today.replace(month=1, day=1)
    income_total = Income.objects.filter(date__gte=year_start).aggregate(s=Sum("amount"))["s"] or 0
    expense_total = Expense.objects.filter(date__gte=year_start).aggregate(s=Sum("amount"))["s"] or 0
    donation_total = Donation.objects.filter(date__gte=year_start).aggregate(s=Sum("amount"))["s"] or 0
    salary_total = SalaryPayment.objects.filter(status="paid").aggregate(s=Sum("amount"))["s"] or 0
    outstanding = FeeInvoice.objects.exclude(status="paid")
    outstanding_total = sum((inv.balance for inv in outstanding), Decimal("0"))
    # By category
    by_category = (Expense.objects.values("category")
                   .annotate(total=Sum("amount")).order_by("-total"))
    by_source = (Income.objects.values("source")
                 .annotate(total=Sum("amount")).order_by("-total"))

    return render(request, "erp/finance_report.html", {
        "income_total": income_total,
        "expense_total": expense_total,
        "donation_total": donation_total,
        "salary_total": salary_total,
        "outstanding_total": outstanding_total,
        "net": (income_total or 0) - (expense_total or 0),
        "by_category": by_category,
        "by_source": by_source,
    })
