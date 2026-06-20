from django import forms
from .models import (
    SchoolClass, Subject, Student, Teacher, Attendance, Grade,
    FeeStructure, FeeInvoice, FeePayment, SalaryPayment, Expense, Income,
    Donor, Donation, Employee, LeaveRequest, AcademicYear,
)


_DATE = forms.DateInput(attrs={"type": "date"})


class AcademicYearForm(forms.ModelForm):
    class Meta:
        model = AcademicYear
        fields = "__all__"
        widgets = {"start_date": _DATE, "end_date": _DATE}


class SchoolClassForm(forms.ModelForm):
    class Meta:
        model = SchoolClass
        fields = "__all__"


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = "__all__"


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        exclude = ["enrollment_date"]
        widgets = {"date_of_birth": _DATE, "address": forms.Textarea(attrs={"rows": 2})}


class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = "__all__"
        widgets = {"hire_date": _DATE}


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = "__all__"
        widgets = {"date": _DATE}


class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        exclude = ["recorded_at"]


class FeeStructureForm(forms.ModelForm):
    class Meta:
        model = FeeStructure
        fields = "__all__"


class FeeInvoiceForm(forms.ModelForm):
    class Meta:
        model = FeeInvoice
        exclude = ["status", "issued_date", "amount_paid"]
        widgets = {"due_date": _DATE, "notes": forms.Textarea(attrs={"rows": 2})}


class FeePaymentForm(forms.ModelForm):
    class Meta:
        model = FeePayment
        exclude = ["received_by", "invoice"]
        widgets = {"paid_on": _DATE}


class SalaryPaymentForm(forms.ModelForm):
    class Meta:
        model = SalaryPayment
        fields = "__all__"
        widgets = {"paid_date": _DATE}


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        exclude = ["recorded_by"]
        widgets = {"date": _DATE, "note": forms.Textarea(attrs={"rows": 2})}


class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = "__all__"
        widgets = {"date": _DATE, "note": forms.Textarea(attrs={"rows": 2})}


class DonorForm(forms.ModelForm):
    class Meta:
        model = Donor
        fields = "__all__"
        widgets = {"address": forms.Textarea(attrs={"rows": 2}),
                   "notes": forms.Textarea(attrs={"rows": 2})}


class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = "__all__"
        widgets = {"date": _DATE, "note": forms.Textarea(attrs={"rows": 2})}


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = "__all__"
        widgets = {"hire_date": _DATE}


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        exclude = ["status", "decided_by", "decided_at"]
        widgets = {"start_date": _DATE, "end_date": _DATE,
                   "reason": forms.Textarea(attrs={"rows": 2})}
