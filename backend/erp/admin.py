from django.contrib import admin
from . import models

for m in [
    models.AcademicYear, models.SchoolClass, models.Subject, models.Student,
    models.Teacher, models.Attendance, models.Grade, models.FeeStructure,
    models.FeeInvoice, models.FeePayment, models.SalaryPayment, models.Expense,
    models.Income, models.Donor, models.Donation, models.Employee, models.LeaveRequest,
    models.PaymentTransaction,
]:
    admin.site.register(m)
