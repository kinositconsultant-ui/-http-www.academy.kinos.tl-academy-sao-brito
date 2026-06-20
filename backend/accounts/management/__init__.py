"""Seed initial data: school profile, admin user, sample academy data."""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from accounts.models import User, School
from erp.models import (
    AcademicYear, SchoolClass, Subject, Student, Teacher,
    FeeStructure, FeeInvoice, FeePayment, SalaryPayment,
    Expense, Income, Donor, Donation, Employee, LeaveRequest, Grade, Attendance,
)


class Command(BaseCommand):
    help = "Seed Academy ERP with starter data."

    def handle(self, *args, **opts):
        # School profile
        school, created = School.objects.get_or_create(
            id=1,
            defaults={
                "name": "Instituto São João de Brito",
                "registration_no": "ISJB-2026-001",
                "address": "Av. Principal, Luanda, Angola",
                "phone": "+244 900 000 000",
                "email": "secretaria@isjb.edu",
                "website": "https://isjb.edu",
                "founded_date": date(1985, 9, 1),
                "motto": "Saber, Servir, Construir",
                "currency": "AOA",
            },
        )
        if not created:
            school.name = "Instituto São João de Brito"
            if not school.motto:
                school.motto = "Saber, Servir, Construir"
            if not school.currency or school.currency == "USD":
                school.currency = "AOA"
            school.save()

        # Admin user
        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@isjb.edu",
                "first_name": "System",
                "last_name": "Administrator",
                "role": "admin",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        admin.set_password("admin123")
        admin.is_staff = True
        admin.is_superuser = True
        admin.role = "admin"
        admin.save()

        # Roles
        for u, pwd, role in [
            ("accountant", "account123", "accountant"),
            ("hrmanager", "hr123456", "hr"),
            ("teacher1", "teach123", "teacher"),
        ]:
            user, c = User.objects.get_or_create(username=u, defaults={"role": role})
            user.set_password(pwd)
            user.role = role
            user.save()

        # Academic Year
        year, _ = AcademicYear.objects.get_or_create(
            name="2025-2026",
            defaults={"start_date": date(2025, 9, 1), "end_date": date(2026, 7, 31),
                      "is_current": True},
        )

        # Classes
        classes = []
        for name, section, level in [
            ("Grade 9", "A", "Secondary"),
            ("Grade 10", "A", "Secondary"),
            ("Grade 11", "B", "Secondary"),
            ("Grade 12", "A", "Secondary"),
        ]:
            c, _ = SchoolClass.objects.get_or_create(
                name=name, section=section, defaults={"level": level, "capacity": 35})
            classes.append(c)

        # Subjects
        for code, name, cls in [
            ("MATH101", "Mathematics", classes[1]),
            ("PORT101", "Português", classes[1]),
            ("PHYS201", "Physics", classes[2]),
            ("CHEM201", "Chemistry", classes[2]),
            ("HIST101", "History", classes[0]),
        ]:
            Subject.objects.get_or_create(code=code, defaults={"name": name, "school_class": cls})

        # Teachers
        teachers_data = [
            ("EMP001", "Maria", "Silva", "Master's in Mathematics", "Mathematics", 350000),
            ("EMP002", "João", "Pereira", "PhD in Physics", "Physics & Chemistry", 420000),
            ("EMP003", "Ana", "Costa", "Bachelor in Linguistics", "Portuguese", 280000),
        ]
        teachers = []
        for emp, fn, ln, qual, spec, sal in teachers_data:
            t, _ = Teacher.objects.get_or_create(
                employee_no=emp,
                defaults={"first_name": fn, "last_name": ln, "email": f"{fn.lower()}@isjb.edu",
                          "phone": "+244 900 100 200", "qualification": qual,
                          "specialization": spec, "hire_date": date(2020, 9, 1),
                          "monthly_salary": Decimal(sal)},
            )
            teachers.append(t)

        # Students
        student_data = [
            ("STU2026001", "Pedro", "Almeida", "M", classes[1], "Carlos Almeida"),
            ("STU2026002", "Beatriz", "Santos", "F", classes[1], "Helena Santos"),
            ("STU2026003", "Miguel", "Fernandes", "M", classes[2], "António Fernandes"),
            ("STU2026004", "Sofia", "Lopes", "F", classes[2], "Marta Lopes"),
            ("STU2026005", "Tiago", "Rodrigues", "M", classes[0], "Rui Rodrigues"),
            ("STU2026006", "Inês", "Carvalho", "F", classes[3], "Paulo Carvalho"),
        ]
        students = []
        for adm, fn, ln, g, cls, parent in student_data:
            s, _ = Student.objects.get_or_create(
                admission_no=adm,
                defaults={"first_name": fn, "last_name": ln, "gender": g,
                          "school_class": cls, "parent_name": parent,
                          "parent_phone": "+244 923 000 000",
                          "parent_email": f"{parent.split()[0].lower()}@example.com",
                          "address": "Luanda, Angola"},
            )
            students.append(s)

        # Fee structures
        for cls in classes:
            FeeStructure.objects.get_or_create(
                name=f"Tuition {cls.name}",
                school_class=cls,
                defaults={"amount": Decimal("180000"), "frequency": "term"},
            )

        # Invoices + payments
        today = timezone.now().date()
        for i, st in enumerate(students[:4]):
            inv, c = FeeInvoice.objects.get_or_create(
                student=st, title="Tuition - Term 1",
                defaults={"amount": Decimal("180000"),
                          "due_date": today + timedelta(days=15 - i*5)},
            )
            if c and i < 2:
                FeePayment.objects.create(
                    invoice=inv, amount=Decimal("180000") if i == 0 else Decimal("90000"),
                    method="bank", reference=f"TRX{i}1023", paid_on=today - timedelta(days=2),
                    received_by=admin,
                )
                inv.amount_paid = inv.payments.aggregate_amount()["s"] if False else inv.payments.first().amount
                inv.refresh_status()
                inv.save()
                Income.objects.create(
                    title=f"Fee payment - {st.full_name}", source="fees",
                    amount=inv.amount_paid, date=today - timedelta(days=2),
                    note=f"Invoice #{inv.id}",
                )

        # Salaries
        for t in teachers:
            SalaryPayment.objects.get_or_create(
                teacher=t, month="January 2026",
                defaults={"amount": t.monthly_salary, "bonus": Decimal("0"),
                          "deductions": Decimal("0"), "status": "pending"},
            )

        # Expenses
        for title, cat, amt in [
            ("Electricity bill", "utilities", 45000),
            ("Office supplies", "supplies", 18000),
            ("Bus maintenance", "transport", 32000),
        ]:
            Expense.objects.get_or_create(
                title=title, defaults={"category": cat, "amount": Decimal(amt),
                                       "date": today - timedelta(days=5),
                                       "paid_to": "Vendor", "recorded_by": admin},
            )

        # Donors + donations
        for name, org, email, amt, purpose in [
            ("Fundação Lumière", "Fundação Lumière", "contact@lumiere.org", 500000, "scholarship"),
            ("Dr. António Cabral", "", "antonio@example.com", 150000, "books"),
            ("Empresa BetaTech", "BetaTech S.A.", "donations@beta.com", 800000, "infrastructure"),
        ]:
            d, _ = Donor.objects.get_or_create(
                name=name, defaults={"organization": org, "email": email,
                                     "phone": "+244 900 555 000",
                                     "address": "Luanda, Angola"},
            )
            dn, c = Donation.objects.get_or_create(
                donor=d, amount=Decimal(amt), date=today - timedelta(days=10),
                defaults={"purpose": purpose, "receipt_no": f"DON-{d.id}-001",
                          "note": "Annual contribution"},
            )
            if c:
                Income.objects.create(
                    title=f"Donation - {d.name}", source="donation",
                    amount=dn.amount, date=dn.date,
                    note=f"Purpose: {dn.get_purpose_display()}",
                )

        # HR employees
        for emp_no, fn, ln, des, dep, sal in [
            ("HR001", "Carla", "Mendes", "HR Manager", "hr", 320000),
            ("HR002", "Rui", "Bastos", "Accountant", "finance", 290000),
            ("HR003", "Lúcia", "Vieira", "Secretary", "admin", 180000),
        ]:
            Employee.objects.get_or_create(
                employee_no=emp_no,
                defaults={"first_name": fn, "last_name": ln, "designation": des,
                          "department": dep, "hire_date": date(2022, 1, 15),
                          "salary": Decimal(sal),
                          "email": f"{fn.lower()}@isjb.edu",
                          "phone": "+244 900 200 100"},
            )

        # Sample grades
        subj = Subject.objects.first()
        if subj:
            for s in students[:3]:
                Grade.objects.get_or_create(
                    student=s, subject=subj, exam_name="Midterm",
                    defaults={"score": Decimal("78"), "total": Decimal("100")},
                )

        # Sample attendance
        for s in students[:3]:
            Attendance.objects.get_or_create(
                student=s, date=today,
                defaults={"status": "present"},
            )

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete. School: {school.name}\n"
            "Login: admin / admin123"))
