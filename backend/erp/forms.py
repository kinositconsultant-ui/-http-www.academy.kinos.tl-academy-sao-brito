from django import forms
from .models import (
    SchoolClass, Subject, Student, Teacher, Attendance, Grade,
    FeeStructure, FeeInvoice, FeePayment, SalaryPayment, Expense, Income,
    Donor, Donation, Employee, LeaveRequest, AcademicYear, CreditNote,
    JobPosting, Candidate, TrainingProgram, TrainingEnrollment,
    PerformanceReview, EmployeeAttendance, InventoryCategory, InventoryItem,
    InventoryAssignment, TeachingDocument,
    Assignment, AssignmentSubmission, Announcement, CalendarEvent,
    StudentDocument, LessonPlan, LearningMaterial,
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


# ---------- Phase 1 — Academic & Communication ----------


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = [
            "title", "title_pt", "title_tet", "description",
            "subject", "class_room", "teacher", "academic_year",
            "term", "max_score", "due_at", "attachment", "is_published",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "due_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
        help_texts = {
            "title_pt": "Português (optional)",
            "title_tet": "Tetum (optional)",
            "attachment": "Optional reference PDF/image for students.",
        }


class AssignmentGradeForm(forms.ModelForm):
    """Used by teachers to grade a submission. Optionally promotes the score
    into the formal Grade table so it appears in the report card."""
    create_grade_entry = forms.BooleanField(
        required=False, initial=False,
        help_text="Also create a Grade row so this score appears in the report card.")

    class Meta:
        model = AssignmentSubmission
        fields = ["score", "feedback"]
        widgets = {"feedback": forms.Textarea(attrs={"rows": 3})}


class StudentSubmissionForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ["text_answer", "file"]
        widgets = {"text_answer": forms.Textarea(attrs={"rows": 6})}
        help_texts = {
            "text_answer": "Type your answer here (optional if you upload a file).",
            "file": "Attach a PDF / image / document (optional if you write a text answer).",
        }


class AnnouncementForm(forms.ModelForm):
    send_email = forms.BooleanField(
        required=False, initial=True,
        help_text="Send email to recipients on publish (MOCKED until SendGrid key is set).")

    class Meta:
        model = Announcement
        fields = [
            "title", "title_pt", "title_tet",
            "body", "body_pt", "body_tet",
            "audience", "audience_classes", "is_pinned", "expires_at",
        ]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 5}),
            "body_pt": forms.Textarea(attrs={"rows": 3}),
            "body_tet": forms.Textarea(attrs={"rows": 3}),
            "audience_classes": forms.CheckboxSelectMultiple,
            "expires_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
        help_texts = {
            "audience_classes": "Optional — restrict to specific classes. Leave empty for all classes in the audience.",
            "expires_at": "Optional — auto-hide after this date/time.",
        }


class CalendarEventForm(forms.ModelForm):
    class Meta:
        model = CalendarEvent
        fields = [
            "title", "title_pt", "title_tet", "description",
            "event_type", "start_at", "end_at", "all_day",
            "location", "audience", "audience_classes",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "start_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "audience_classes": forms.CheckboxSelectMultiple,
        }



class StudentDocumentForm(forms.ModelForm):
    class Meta:
        model = StudentDocument
        fields = ["doc_type", "title", "file", "issued_date", "expires_at", "notes"]
        widgets = {
            "issued_date": _DATE,
            "expires_at": _DATE,
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "title": "Optional. Defaults to the document type if blank.",
            "expires_at": "Optional. Documents in the next 30 days are flagged on the student profile.",
        }


class LessonPlanForm(forms.ModelForm):
    class Meta:
        model = LessonPlan
        fields = ["title", "title_pt", "title_tet",
                  "subject", "class_room", "teacher", "week_start",
                  "objectives", "activities", "materials",
                  "file", "is_published"]
        widgets = {
            "week_start": _DATE,
            "objectives": forms.Textarea(attrs={"rows": 3}),
            "activities": forms.Textarea(attrs={"rows": 4}),
            "materials": forms.Textarea(attrs={"rows": 2}),
        }
        help_texts = {
            "teacher": "Required when an admin creates the plan; auto-filled for teachers.",
        }




class LearningMaterialForm(forms.ModelForm):
    class Meta:
        model = LearningMaterial
        fields = ["title", "title_pt", "title_tet",
                  "subject", "class_room", "teacher",
                  "material_type", "url", "file",
                  "description", "week_no", "is_published"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
        help_texts = {
            "url": "YouTube / Vimeo URL for video, or any external link.",
            "file": "Upload PDF / slides / document. Optional if `url` is set.",
            "class_room": "Leave empty to share with every class taking this subject.",
            "teacher": "Required when an admin uploads; auto-filled for teachers.",
        }

    def clean(self):
        cleaned = super().clean()
        mtype = cleaned.get("material_type")
        url = cleaned.get("url")
        f = cleaned.get("file")
        if mtype in ("video", "link") and not url:
            self.add_error("url", f"A URL is required for {mtype} material.")
        if mtype in ("pdf", "slides", "other") and not f and not url:
            self.add_error("file", "Either upload a file or provide a URL.")
        return cleaned
