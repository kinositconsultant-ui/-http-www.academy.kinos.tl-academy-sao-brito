"""Seed initial data for Academy ERP.

Usage: python manage.py shell < scripts/seed.py
Or: python scripts/seed.py
"""
import os, sys, django
from datetime import date, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "academy_erp.settings")
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import School
from erp.models import (
    AcademicYear, SchoolClass, Subject, Student, Teacher,
    FeeStructure, FeeInvoice, Donor, Donation, Expense, Income,
    Employee, SalaryPayment, Grade, Attendance, LeaveRequest,
)

User = get_user_model()

# ---------- Admin user (idempotent) ----------
admin, created = User.objects.get_or_create(
    username="admin",
    defaults={"email": "admin@isjb.edu", "is_staff": True, "is_superuser": True,
              "first_name": "Director", "last_name": "Geral", "role": "admin"},
)
if created or not admin.has_usable_password():
    admin.set_password("admin123")
    admin.is_staff = True
    admin.is_superuser = True
    admin.save()
    print(f"[seed] admin user ready (admin/admin123)")

# Additional role-based users
for uname, fname, lname, role, email in [
    ("accountant", "Sofia", "Costa", "accountant", "accountant@isjb.edu"),
    ("hr", "Miguel", "Santos", "hr", "hr@isjb.edu"),
    ("principal", "Beatriz", "Almeida", "principal", "principal@isjb.edu"),
]:
    u, c = User.objects.get_or_create(username=uname, defaults={
        "first_name": fname, "last_name": lname, "role": role, "email": email,
    })
    if c:
        u.set_password("password123")
        u.save()

# ---------- School profile ----------
if not School.objects.exists():
    School.objects.create(
        name="Instituto São João de Brito",
        registration_no="REG-ISJB-001",
        address="Av. da República, 123, Lisboa, Portugal",
        phone="+351 21 000 0000",
        email="contact@isjb.edu",
        website="https://isjb.edu",
        motto="Scientia · Caritas · Veritas",
        founded_date=date(1948, 9, 15),
        currency="EUR",
    )
    print("[seed] School profile: Instituto São João de Brito")
else:
    # Update existing if name is generic
    s = School.objects.first()
    if s.name != "Instituto São João de Brito":
        s.name = "Instituto São João de Brito"
        s.registration_no = s.registration_no or "REG-ISJB-001"
        s.address = s.address or "Av. da República, 123, Lisboa, Portugal"
        s.phone = s.phone or "+351 21 000 0000"
        s.email = s.email or "contact@isjb.edu"
        s.website = s.website or "https://isjb.edu"
        s.motto = s.motto or "Scientia · Caritas · Veritas"
        s.currency = "EUR"
        s.save()
        print("[seed] School profile updated to Instituto São João de Brito")

# ---------- Academic year ----------
if not AcademicYear.objects.exists():
    AcademicYear.objects.create(name="2025-2026",
        start_date=date(2025, 9, 1), end_date=date(2026, 7, 15), is_current=True)

# ---------- Classes ----------
classes_data = [("Year 7", "A", "Lower Secondary"), ("Year 7", "B", "Lower Secondary"),
                ("Year 10", "A", "Upper Secondary"), ("Year 12", "A", "Upper Secondary")]
classes = []
for name, sec, level in classes_data:
    c, _ = SchoolClass.objects.get_or_create(name=name, section=sec, defaults={"level": level})
    classes.append(c)

# ---------- Subjects ----------
subjects_data = [("Mathematics", "MATH101"), ("Portuguese", "PORT101"),
                 ("English", "ENG101"), ("History", "HIST101"),
                 ("Physics", "PHY201"), ("Biology", "BIO201")]
subjects = []
for name, code in subjects_data:
    s, _ = Subject.objects.get_or_create(code=code, defaults={"name": name, "school_class": classes[0]})
    subjects.append(s)

# ---------- Teachers ----------
teachers_data = [
    ("T-001", "Ana", "Ferreira", "ana.ferreira@isjb.edu", "+351 91 123 4567", "MA Mathematics", "Mathematics", Decimal("2400")),
    ("T-002", "João", "Silva", "joao.silva@isjb.edu", "+351 91 234 5678", "PhD Physics", "Physics", Decimal("2800")),
    ("T-003", "Maria", "Pereira", "maria.pereira@isjb.edu", "+351 91 345 6789", "BA Languages", "Portuguese / English", Decimal("2200")),
    ("T-004", "Carlos", "Mendes", "carlos.mendes@isjb.edu", "+351 91 456 7890", "MA History", "History", Decimal("2300")),
]
teachers = []
for empno, fn, ln, em, ph, q, sp, sal in teachers_data:
    t, c = Teacher.objects.get_or_create(employee_no=empno, defaults={
        "first_name": fn, "last_name": ln, "email": em, "phone": ph,
        "qualification": q, "specialization": sp, "monthly_salary": sal,
        "hire_date": date(2022, 9, 1),
    })
    teachers.append(t)
    if c:
        t.subjects.add(subjects[0])

# ---------- Students ----------
students_data = [
    ("ADM-1001", "Lucas", "Oliveira", "M", date(2010, 5, 12), 0, "Helena Oliveira", "+351 92 111 2222"),
    ("ADM-1002", "Sofia", "Rodrigues", "F", date(2010, 8, 22), 0, "Pedro Rodrigues", "+351 92 222 3333"),
    ("ADM-1003", "Miguel", "Costa", "M", date(2010, 1, 4), 1, "Inês Costa", "+351 92 333 4444"),
    ("ADM-1004", "Beatriz", "Santos", "F", date(2007, 11, 9), 2, "Rui Santos", "+351 92 444 5555"),
    ("ADM-1005", "Tiago", "Almeida", "M", date(2007, 3, 30), 2, "Mariana Almeida", "+351 92 555 6666"),
    ("ADM-1006", "Rita", "Carvalho", "F", date(2005, 6, 18), 3, "Pedro Carvalho", "+351 92 666 7777"),
    ("ADM-1007", "Daniel", "Sousa", "M", date(2005, 9, 27), 3, "Sara Sousa", "+351 92 777 8888"),
]
students = []
for adm, fn, ln, g, dob, cidx, pn, pp in students_data:
    s, _ = Student.objects.get_or_create(admission_no=adm, defaults={
        "first_name": fn, "last_name": ln, "gender": g, "date_of_birth": dob,
        "school_class": classes[cidx], "parent_name": pn, "parent_phone": pp,
        "parent_email": f"{fn.lower()}.parent@example.com",
        "address": "Lisboa, Portugal",
    })
    students.append(s)

# ---------- Fee Structures ----------
for cl in classes:
    FeeStructure.objects.get_or_create(
        name=f"Tuition Term 1 - {cl}",
        school_class=cl,
        defaults={"amount": Decimal("850"), "frequency": "term"},
    )

# ---------- Invoices + payments ----------
today = date.today()
if not FeeInvoice.objects.exists():
    for i, st in enumerate(students):
        inv = FeeInvoice.objects.create(
            student=st, title="Tuition - Term 1",
            amount=Decimal("850"),
            due_date=today + timedelta(days=10 - i*3),
            notes="Term fee 2025/26",
        )
        # Half of students paid in full, others partially
        if i % 2 == 0:
            from erp.models import FeePayment
            FeePayment.objects.create(invoice=inv, amount=inv.amount, method="bank",
                reference=f"TX-{1000+i}", paid_on=today - timedelta(days=2),
                received_by=admin)
            inv.amount_paid = inv.amount
        elif i % 3 == 0:
            from erp.models import FeePayment
            FeePayment.objects.create(invoice=inv, amount=Decimal("400"), method="cash",
                reference="", paid_on=today - timedelta(days=4), received_by=admin)
            inv.amount_paid = Decimal("400")
        inv.refresh_status(); inv.save()

# ---------- Donors & donations ----------
donors_data = [
    ("Fundação Calouste", "Calouste Foundation", "info@calouste.org"),
    ("Família Mendes", "", "mendes@example.com"),
    ("Banco Lusitano", "Banco Lusitano S.A.", "csr@lusitano.pt"),
]
donors = []
for name, org, em in donors_data:
    d, _ = Donor.objects.get_or_create(name=name, defaults={"organization": org, "email": em,
                                                            "phone": "+351 21 999 9999"})
    donors.append(d)

if not Donation.objects.exists():
    Donation.objects.create(donor=donors[0], amount=Decimal("5000"), purpose="scholarship",
        date=today - timedelta(days=30), receipt_no="RCP-2025-001",
        note="Scholarship for 5 students")
    Donation.objects.create(donor=donors[1], amount=Decimal("750"), purpose="books",
        date=today - timedelta(days=12), receipt_no="RCP-2025-002")
    Donation.objects.create(donor=donors[2], amount=Decimal("12000"), purpose="infrastructure",
        date=today - timedelta(days=4), receipt_no="RCP-2025-003",
        note="Library renovation")
    for don in Donation.objects.all():
        Income.objects.get_or_create(title=f"Donation - {don.donor.name}",
            source="donation", amount=don.amount, date=don.date,
            defaults={"note": don.get_purpose_display()})

# ---------- Expenses ----------
if not Expense.objects.exists():
    Expense.objects.create(title="Electricity bill - October", category="utilities",
        amount=Decimal("420"), paid_to="EDP", date=today - timedelta(days=8), recorded_by=admin)
    Expense.objects.create(title="Stationery & lab supplies", category="supplies",
        amount=Decimal("310"), paid_to="Papelaria Central", date=today - timedelta(days=14), recorded_by=admin)
    Expense.objects.create(title="School bus diesel", category="transport",
        amount=Decimal("680"), paid_to="Galp", date=today - timedelta(days=3), recorded_by=admin)

# ---------- Salaries ----------
if not SalaryPayment.objects.exists():
    for t in teachers:
        SalaryPayment.objects.create(teacher=t, month="January 2026",
            amount=t.monthly_salary, bonus=Decimal("50"), deductions=Decimal("0"),
            status="pending")

# ---------- Employees (HR) ----------
emp_data = [
    ("EMP-001", "Patrícia", "Lopes", "Receptionist", "admin", Decimal("1100")),
    ("EMP-002", "Bruno", "Tavares", "Maintenance Supervisor", "maintenance", Decimal("1300")),
    ("EMP-003", "Catarina", "Neves", "IT Officer", "it", Decimal("1800")),
]
for empno, fn, ln, des, dep, sal in emp_data:
    Employee.objects.get_or_create(employee_no=empno, defaults={
        "first_name": fn, "last_name": ln, "designation": des,
        "department": dep, "salary": sal, "hire_date": date(2023, 1, 15),
        "email": f"{fn.lower()}@isjb.edu",
    })

# ---------- Grades sample ----------
if not Grade.objects.exists() and students and subjects:
    for i, st in enumerate(students[:4]):
        Grade.objects.create(student=st, subject=subjects[i % len(subjects)],
            exam_name="Midterm Test", score=Decimal(str(70 + i*5)), total=Decimal("100"))

# ---------- Attendance sample ----------
if not Attendance.objects.exists():
    for st in students[:5]:
        Attendance.objects.create(student=st, date=today, status="present")

# ---------- Leave sample ----------
if not LeaveRequest.objects.exists():
    emp = Employee.objects.first()
    if emp:
        LeaveRequest.objects.create(employee=emp, leave_type="annual",
            start_date=today + timedelta(days=10),
            end_date=today + timedelta(days=14),
            reason="Family vacation")

print("[seed] Done.")
