from django.db import models
from django.conf import settings


# ---------- Academy ----------

class AcademicYear(models.Model):
    name = models.CharField(max_length=50, unique=True)  # 2025-2026
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class SchoolClass(models.Model):
    name = models.CharField(max_length=80)  # Grade 10
    section = models.CharField(max_length=10, blank=True)  # A / B
    level = models.CharField(max_length=40, blank=True)  # Primary / Secondary
    capacity = models.PositiveIntegerField(default=40)

    class Meta:
        ordering = ["name", "section"]
        unique_together = ("name", "section")

    def __str__(self):
        return f"{self.name}{(' - ' + self.section) if self.section else ''}"


class Subject(models.Model):
    name = models.CharField(max_length=80)
    code = models.CharField(max_length=20, unique=True)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name="subjects")

    def __str__(self):
        return f"{self.name} ({self.code})"


class IDType(models.TextChoices):
    BI = "bi", "BI"
    ELECTORAL = "electoral", "Electoral"
    PASSPORT = "passport", "Passport"


class Student(models.Model):
    GENDER_CHOICES = [("M", "Male"), ("F", "Female"), ("O", "Other")]

    admission_no = models.CharField(max_length=30, unique=True)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default="M")
    date_of_birth = models.DateField(null=True, blank=True)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name="students")

    # Parents (split)
    father_name = models.CharField(max_length=120, blank=True)
    mother_name = models.CharField(max_length=120, blank=True)
    parent_phone = models.CharField(max_length=30, blank=True)
    parent_email = models.EmailField(blank=True)

    # Identification
    id_type = models.CharField(max_length=20, choices=IDType.choices,
                               blank=True, default="")
    id_number = models.CharField(max_length=60, blank=True)

    # Structured address
    village = models.CharField(max_length=100, blank=True)
    subvillage = models.CharField(max_length=100, blank=True)
    subdistrict = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True, help_text="Additional address details (optional)")

    # Documents
    school_certificate = models.FileField(
        upload_to="student_docs/certificates/", blank=True, null=True,
        help_text="Upload the student's last school certificate.")
    photo = models.ImageField(upload_to="students/", blank=True, null=True)

    enrollment_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # Parent portal access (links student → User with role=parent)
    parent_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="children",
        limit_choices_to={"role": "parent"},
        help_text="Parent accounts that can view this student in the parent portal.",
    )

    # Student self-service portal (links student → User with role=student)
    student_user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="student_profile",
        limit_choices_to={"role": "student"},
        help_text="Student account used to log in to the student portal.",
    )

    class Meta:
        ordering = ["-id"]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def parents_display(self):
        parts = []
        if self.father_name:
            parts.append(f"Father: {self.father_name}")
        if self.mother_name:
            parts.append(f"Mother: {self.mother_name}")
        return " · ".join(parts) or "—"

    @property
    def full_address(self):
        parts = [self.village, self.subvillage, self.subdistrict, self.district]
        parts = [p for p in parts if p]
        if self.address:
            parts.append(self.address)
        return ", ".join(parts) or "—"

    def __str__(self):
        return f"{self.full_name} [{self.admission_no}]"


class Teacher(models.Model):
    employee_no = models.CharField(max_length=30, unique=True)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)

    # Parents
    father_name = models.CharField(max_length=120, blank=True)
    mother_name = models.CharField(max_length=120, blank=True)

    # Identification
    id_type = models.CharField(max_length=20, choices=IDType.choices,
                               blank=True, default="")
    id_number = models.CharField(max_length=60, blank=True)

    # Academic background
    qualification = models.CharField(max_length=120, blank=True,
                                     help_text="Highest qualification, e.g. 'MA Mathematics'")
    specialization = models.CharField(max_length=120, blank=True)
    education_background = models.TextField(
        blank=True, help_text="Schools attended, degrees, certifications, year-by-year.")
    diploma_certificate = models.FileField(
        upload_to="teacher_docs/diplomas/", blank=True, null=True,
        help_text="Upload diploma / certificate scan.")

    # Structured address
    village = models.CharField(max_length=100, blank=True)
    subvillage = models.CharField(max_length=100, blank=True)
    subdistrict = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True, help_text="Additional address details (optional)")

    hire_date = models.DateField(null=True, blank=True)
    monthly_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subjects = models.ManyToManyField(Subject, blank=True, related_name="teachers")
    photo = models.ImageField(upload_to="teachers/", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # Teacher self-service portal (links Teacher → User with role=teacher)
    teacher_user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="teacher_profile",
        limit_choices_to={"role": "teacher"},
        help_text="Teacher account used to log in to the teacher portal.",
    )

    class Meta:
        ordering = ["-id"]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def parents_display(self):
        parts = []
        if self.father_name:
            parts.append(f"Father: {self.father_name}")
        if self.mother_name:
            parts.append(f"Mother: {self.mother_name}")
        return " · ".join(parts) or "—"

    @property
    def full_address(self):
        parts = [self.village, self.subvillage, self.subdistrict, self.district]
        parts = [p for p in parts if p]
        if self.address:
            parts.append(self.address)
        return ", ".join(parts) or "—"

    def __str__(self):
        return f"{self.full_name} [{self.employee_no}]"


class Attendance(models.Model):
    STATUS_CHOICES = [
        ("present", "Present"),
        ("absent", "Absent"),
        ("late", "Late"),
        ("excused", "Excused"),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="attendance")
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="present")
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ("student", "date")
        ordering = ["-date"]


class Grade(models.Model):
    SEMESTER_CHOICES = [
        ("s1", "Semester 1"),
        ("s2", "Semester 2"),
        ("mid", "Midterm"),
        ("final", "Final"),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="grades")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="grades")
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.SET_NULL, null=True, blank=True, related_name="grades",
    )
    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, default="s1")
    exam_name = models.CharField(max_length=80)  # Midterm, Final, etc.
    score = models.DecimalField(max_digits=6, decimal_places=2)
    total = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    passing_pct = models.DecimalField(max_digits=5, decimal_places=2, default=50,
                                      help_text="Minimum percentage required to pass")
    recorded_at = models.DateField(auto_now_add=True)

    @property
    def percentage(self):
        try:
            return round((float(self.score) / float(self.total)) * 100, 2)
        except (ZeroDivisionError, TypeError):
            return 0

    @property
    def is_pass(self):
        return self.percentage >= float(self.passing_pct or 50)

    @property
    def letter(self):
        p = self.percentage
        if p >= 90:
            return "A"
        if p >= 80:
            return "B"
        if p >= 70:
            return "C"
        if p >= 60:
            return "D"
        return "F"

    class Meta:
        ordering = ["-recorded_at"]


# ---------- Finance ----------

class FeeStructure(models.Model):
    FREQUENCY = [("monthly", "Monthly"), ("term", "Per Term"), ("annual", "Annual")]
    name = models.CharField(max_length=120)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="fee_structures")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY, default="term")

    def __str__(self):
        return f"{self.name} - {self.school_class} ({self.amount})"


class FeeInvoice(models.Model):
    STATUS = [("pending", "Pending"), ("paid", "Paid"),
              ("partial", "Partial"), ("overdue", "Overdue")]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="invoices")
    title = models.CharField(max_length=120)  # Tuition - Term 1
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    due_date = models.DateField()
    issued_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-issued_date"]

    @property
    def balance(self):
        return (self.amount or 0) - (self.amount_paid or 0)

    def refresh_status(self):
        if self.amount_paid >= self.amount:
            self.status = "paid"
        elif self.amount_paid > 0:
            self.status = "partial"
        else:
            from django.utils.timezone import now
            self.status = "overdue" if self.due_date < now().date() else "pending"


class FeePayment(models.Model):
    METHOD = [("cash", "Cash"), ("bank", "Bank Transfer"),
              ("card", "Card"), ("mobile", "Mobile Money"), ("other", "Other")]
    invoice = models.ForeignKey(FeeInvoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD, default="cash")
    reference = models.CharField(max_length=120, blank=True)
    paid_on = models.DateField()
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, blank=True)

    class Meta:
        ordering = ["-paid_on"]


class SalaryPayment(models.Model):
    STATUS = [("pending", "Pending"), ("paid", "Paid")]
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="salary_payments")
    month = models.CharField(max_length=20)  # "Jan 2026"
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    note = models.CharField(max_length=200, blank=True)

    @property
    def net(self):
        return (self.amount or 0) + (self.bonus or 0) - (self.deductions or 0)

    class Meta:
        ordering = ["-id"]


class Expense(models.Model):
    CATEGORY = [
        ("utilities", "Utilities"), ("supplies", "Supplies"),
        ("maintenance", "Maintenance"), ("transport", "Transport"),
        ("marketing", "Marketing"), ("food", "Food/Cafeteria"),
        ("other", "Other"),
    ]
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY, default="other")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_to = models.CharField(max_length=200, blank=True)
    date = models.DateField()
    note = models.TextField(blank=True)
    receipt = models.FileField(upload_to="receipts/", blank=True, null=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, blank=True)

    class Meta:
        ordering = ["-date"]


class Income(models.Model):
    SOURCE = [
        ("fees", "Tuition Fees"), ("donation", "Donation"),
        ("grant", "Grant"), ("event", "Event"),
        ("other", "Other"),
    ]
    title = models.CharField(max_length=200)
    source = models.CharField(max_length=20, choices=SOURCE, default="other")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]


# ---------- Donors ----------

class Donor(models.Model):
    name = models.CharField(max_length=200)
    organization = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.name

    @property
    def total_donated(self):
        return sum((d.amount for d in self.donations.all()), 0)


class Donation(models.Model):
    PURPOSE = [
        ("general", "General Support"), ("scholarship", "Scholarship Fund"),
        ("infrastructure", "Infrastructure"), ("books", "Books & Supplies"),
        ("events", "Events"),
    ]
    donor = models.ForeignKey(Donor, on_delete=models.CASCADE, related_name="donations")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    purpose = models.CharField(max_length=20, choices=PURPOSE, default="general")
    date = models.DateField()
    receipt_no = models.CharField(max_length=50, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]


# ---------- HR ----------

class Employee(models.Model):
    DEPARTMENT = [
        ("academics", "Academics"), ("admin", "Administration"),
        ("finance", "Finance"), ("hr", "Human Resources"),
        ("maintenance", "Maintenance"), ("it", "IT"),
        ("other", "Other"),
    ]
    employee_no = models.CharField(max_length=30, unique=True)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    designation = models.CharField(max_length=120)
    department = models.CharField(max_length=20, choices=DEPARTMENT, default="other")
    hire_date = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-id"]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.full_name} [{self.employee_no}]"


class LeaveRequest(models.Model):
    TYPE = [("annual", "Annual"), ("sick", "Sick"),
            ("maternity", "Maternity"), ("unpaid", "Unpaid"), ("other", "Other")]
    STATUS = [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leaves")
    leave_type = models.CharField(max_length=20, choices=TYPE, default="annual")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def days(self):
        return (self.end_date - self.start_date).days + 1


# ---------- Stripe payment transactions ----------

class PaymentTransaction(models.Model):
    """Audit trail for Stripe Checkout sessions linked to fee invoices."""
    STATUS = [
        ("initiated", "Initiated"),
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("expired", "Expired"),
        ("failed", "Failed"),
    ]
    invoice = models.ForeignKey(FeeInvoice, on_delete=models.CASCADE,
                                related_name="stripe_transactions")
    session_id = models.CharField(max_length=255, unique=True)
    payment_id = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="usd")
    status = models.CharField(max_length=20, choices=STATUS, default="initiated")
    payment_status = models.CharField(max_length=40, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"TX {self.session_id[:12]}… {self.status}"


class SentEmail(models.Model):
    """Audit log of every receipt / notification email (mock or live)."""
    to_email = models.EmailField()
    subject = models.CharField(max_length=200)
    html = models.TextField()
    mode = models.CharField(max_length=10, choices=[("mock", "Mock"), ("live", "Live")], default="mock")
    success = models.BooleanField(default=True)
    error = models.CharField(max_length=300, blank=True)
    invoice = models.ForeignKey(
        FeeInvoice, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sent_emails",
    )
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]


class CreditNote(models.Model):
    """Finance credit note issued to a student.

    Examples: scholarship deduction, refund for overpaid fees, goodwill credit.
    Can optionally be applied against a specific invoice (reducing its balance);
    otherwise the student carries the credit and the admin can later apply it.
    """
    STATUS = [("open", "Open"), ("applied", "Applied"), ("void", "Void")]
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="credit_notes")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=200)
    invoice = models.ForeignKey(
        FeeInvoice, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="credit_notes",
        help_text="Optional invoice this credit was applied against.")
    issued_on = models.DateField(auto_now_add=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="open")
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-issued_on", "-id"]

    def __str__(self):
        return f"CN-{self.id} {self.student.full_name} {self.amount}"




# =====================================================================
# HR — Recruitment, Training, Performance, Employee Attendance, Inventory
# =====================================================================


class JobPosting(models.Model):
    STATUS = [("open", "Open"), ("closed", "Closed"), ("on_hold", "On Hold")]
    title = models.CharField(max_length=160)
    department = models.CharField(max_length=20, choices=Employee.DEPARTMENT, default="other")
    description = models.TextField(blank=True)
    requirements = models.TextField(blank=True)
    salary_range = models.CharField(max_length=80, blank=True, help_text="e.g. USD 800–1,200")
    openings = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=10, choices=STATUS, default="open")
    posted_on = models.DateField(auto_now_add=True)
    closes_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-posted_on", "-id"]

    def __str__(self):
        return f"{self.title} ({self.get_department_display()})"


class Candidate(models.Model):
    STAGE = [
        ("applied", "Applied"), ("screening", "Screening"),
        ("interview", "Interview"), ("offer", "Offer"),
        ("hired", "Hired"), ("rejected", "Rejected"),
    ]
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name="candidates")
    full_name = models.CharField(max_length=160)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    cv = models.FileField(upload_to="cvs/", blank=True, null=True)
    stage = models.CharField(max_length=12, choices=STAGE, default="applied")
    applied_on = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-applied_on", "-id"]

    def __str__(self):
        return f"{self.full_name} → {self.job.title}"


class TrainingProgram(models.Model):
    STATUS = [("scheduled", "Scheduled"), ("ongoing", "Ongoing"),
              ("completed", "Completed"), ("cancelled", "Cancelled")]
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    trainer = models.CharField(max_length=120, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    capacity = models.PositiveIntegerField(default=20)
    status = models.CharField(max_length=10, choices=STATUS, default="scheduled")

    class Meta:
        ordering = ["-start_date", "-id"]

    def __str__(self):
        return self.title

    @property
    def enrolled_count(self):
        return self.enrollments.count()


class TrainingEnrollment(models.Model):
    STATUS = [("enrolled", "Enrolled"), ("completed", "Completed"), ("dropped", "Dropped")]
    program = models.ForeignKey(TrainingProgram, on_delete=models.CASCADE, related_name="enrollments")
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="trainings")
    status = models.CharField(max_length=10, choices=STATUS, default="enrolled")
    enrolled_on = models.DateField(auto_now_add=True)
    completed_on = models.DateField(null=True, blank=True)
    score = models.PositiveIntegerField(null=True, blank=True, help_text="Optional 0–100")
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-enrolled_on", "-id"]
        unique_together = [("program", "employee")]


class PerformanceReview(models.Model):
    RATING = [(1, "1 — Needs Improvement"), (2, "2 — Below Expectations"),
              (3, "3 — Meets Expectations"), (4, "4 — Exceeds Expectations"),
              (5, "5 — Outstanding")]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                 null=True, blank=True)
    period_start = models.DateField()
    period_end = models.DateField()
    rating = models.PositiveSmallIntegerField(choices=RATING, default=3)
    strengths = models.TextField(blank=True)
    improvements = models.TextField(blank=True)
    goals = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-period_end", "-id"]


class EmployeeAttendance(models.Model):
    STATUS = [("present", "Present"), ("absent", "Absent"),
              ("late", "Late"), ("leave", "On Leave"), ("remote", "Remote")]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendance")
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS, default="present")
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-date", "-id"]
        unique_together = [("employee", "date")]


class InventoryCategory(models.Model):
    name = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Inventory categories"

    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    name = models.CharField(max_length=160)
    category = models.ForeignKey(InventoryCategory, on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name="items")
    sku = models.CharField(max_length=60, blank=True)
    quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=0,
        help_text="Below this, the item is flagged as low-stock.")
    location = models.CharField(max_length=120, blank=True)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return self.reorder_level and self.quantity <= self.reorder_level

    @property
    def total_value(self):
        return float(self.unit_cost or 0) * (self.quantity or 0)


class InventoryAssignment(models.Model):
    STATUS = [("assigned", "Assigned"), ("returned", "Returned"), ("lost", "Lost")]
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="assignments")
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="assignments")
    quantity = models.PositiveIntegerField(default=1)
    assigned_on = models.DateField(auto_now_add=True)
    return_by = models.DateField(null=True, blank=True)
    returned_on = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="assigned")
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-assigned_on", "-id"]


class StudentEvaluation(models.Model):
    """Teacher's narrative note / advice for a student (per term)."""
    CATEGORY = [
        ("academic", "Academic"),
        ("behaviour", "Behaviour"),
        ("counselling", "Counselling"),
        ("recognition", "Recognition / Praise"),
        ("other", "Other"),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="evaluations")
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="evaluations_written")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name="evaluations")
    semester = models.CharField(max_length=10, choices=Grade.SEMESTER_CHOICES, default="s1")
    category = models.CharField(max_length=12, choices=CATEGORY, default="academic")
    comment = models.TextField()
    recommendation = models.TextField(blank=True)
    visible_to_parent = models.BooleanField(
        default=True,
        help_text="On by default — note appears on the parent + student portals.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.get_category_display()} · {self.student.full_name}"

