from django import forms
from .models import (
    SchoolClass, Subject, Student, Teacher, Attendance, Grade,
    FeeStructure, FeeInvoice, FeePayment, SalaryPayment, Expense, Income,
    Donor, Donation, Employee, LeaveRequest, AcademicYear, CreditNote,
    JobPosting, Candidate, TrainingProgram, TrainingEnrollment,
    PerformanceReview, EmployeeAttendance, InventoryCategory, InventoryItem,
    InventoryAssignment, TeachingDocument,
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
        widgets = {"exam_name": forms.TextInput(attrs={"placeholder": "e.g. Midterm Math Test"})}


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



class CreditNoteForm(forms.ModelForm):
    class Meta:
        model = CreditNote
        exclude = ["issued_on", "issued_by"]
        widgets = {"note": forms.Textarea(attrs={"rows": 2})}


# ===== HR forms =====

class JobPostingForm(forms.ModelForm):
    class Meta:
        model = JobPosting
        fields = ["title", "department", "description", "requirements",
                  "salary_range", "openings", "status", "closes_on"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3}),
                   "requirements": forms.Textarea(attrs={"rows": 3}),
                   "closes_on": forms.DateInput(attrs={"type": "date"})}


class CandidateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ["job", "full_name", "email", "phone", "cv", "stage", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}


class TrainingProgramForm(forms.ModelForm):
    class Meta:
        model = TrainingProgram
        fields = ["title", "description", "trainer", "start_date", "end_date",
                  "capacity", "status"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3}),
                   "start_date": forms.DateInput(attrs={"type": "date"}),
                   "end_date": forms.DateInput(attrs={"type": "date"})}


class TrainingEnrollmentForm(forms.ModelForm):
    class Meta:
        model = TrainingEnrollment
        fields = ["program", "employee", "status", "score", "note"]


class PerformanceReviewForm(forms.ModelForm):
    class Meta:
        model = PerformanceReview
        fields = ["employee", "period_start", "period_end", "rating",
                  "strengths", "improvements", "goals"]
        widgets = {"strengths": forms.Textarea(attrs={"rows": 2}),
                   "improvements": forms.Textarea(attrs={"rows": 2}),
                   "goals": forms.Textarea(attrs={"rows": 2}),
                   "period_start": forms.DateInput(attrs={"type": "date"}),
                   "period_end": forms.DateInput(attrs={"type": "date"})}


class EmployeeAttendanceForm(forms.ModelForm):
    class Meta:
        model = EmployeeAttendance
        fields = ["employee", "date", "status", "check_in", "check_out", "note"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"}),
                   "check_in": forms.TimeInput(attrs={"type": "time"}),
                   "check_out": forms.TimeInput(attrs={"type": "time"})}


class InventoryCategoryForm(forms.ModelForm):
    class Meta:
        model = InventoryCategory
        fields = ["name"]


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ["name", "category", "sku", "quantity", "reorder_level",
                  "location", "unit_cost", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}


class InventoryAssignmentForm(forms.ModelForm):
    class Meta:
        model = InventoryAssignment
        fields = ["item", "employee", "quantity", "return_by", "status", "note"]
        widgets = {"return_by": forms.DateInput(attrs={"type": "date"})}


class TeachingDocumentForm(forms.ModelForm):
    class Meta:
        model = TeachingDocument
        fields = ["title", "doc_type", "description", "file",
                  "subjects", "academic_year"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
            "subjects": forms.CheckboxSelectMultiple,
        }
        help_texts = {
            "file": "PDF only. Max ~25 MB.",
            "subjects": "Tick the subjects this document is for. Leave all unchecked to share with every teacher.",
        }
