from django.urls import path
from django.views.generic import RedirectView
from . import views
from . import portal_views

urlpatterns = [
    path("", RedirectView.as_view(url="/api/dashboard/", permanent=False)),
    path("dashboard/", views.dashboard, name="dashboard"),

    # Parent portal
    path("parent/", portal_views.parent_dashboard, name="parent_dashboard"),
    path("parent/student/<int:pk>/", portal_views.parent_student_detail, name="parent_student_detail"),

    # Bulk PDF report cards
    path("classes/<int:class_id>/report-cards.zip", portal_views.class_report_cards_zip, name="class_report_cards_zip"),

    # Stripe online payments
    path("invoices/<int:pk>/pay-online/", portal_views.invoice_pay_online, name="invoice_pay_online"),
    path("invoices/<int:pk>/pay-crypto/", portal_views.invoice_pay_crypto, name="invoice_pay_crypto"),
    path("invoices/<int:pk>/payment-status/", portal_views.invoice_payment_status, name="invoice_payment_status"),
    path("webhook/stripe", portal_views.stripe_webhook, name="stripe_webhook"),

    # Academic years
    path("years/", views.academic_year_list, name="academic_year_list"),
    path("years/add/", views.academic_year_create, name="academic_year_create"),
    path("years/<int:pk>/edit/", views.academic_year_edit, name="academic_year_edit"),
    path("years/<int:pk>/delete/", views.academic_year_delete, name="academic_year_delete"),

    # Classes
    path("classes/", views.class_list, name="class_list"),
    path("classes/add/", views.class_create, name="class_create"),
    path("classes/<int:pk>/edit/", views.class_edit, name="class_edit"),
    path("classes/<int:pk>/delete/", views.class_delete, name="class_delete"),

    # Subjects
    path("subjects/", views.subject_list, name="subject_list"),
    path("subjects/add/", views.subject_create, name="subject_create"),
    path("subjects/<int:pk>/edit/", views.subject_edit, name="subject_edit"),
    path("subjects/<int:pk>/delete/", views.subject_delete, name="subject_delete"),

    # Students
    path("students/", views.student_list, name="student_list"),
    path("students/add/", views.student_create, name="student_create"),
    path("students/<int:pk>/", views.student_detail, name="student_detail"),
    path("students/<int:pk>/report-card/", views.student_report_card, name="student_report_card"),
    path("students/<int:pk>/edit/", views.student_edit, name="student_edit"),
    path("students/<int:pk>/delete/", views.student_delete, name="student_delete"),

    # Teachers
    path("teachers/", views.teacher_list, name="teacher_list"),
    path("teachers/add/", views.teacher_create, name="teacher_create"),
    path("teachers/<int:pk>/edit/", views.teacher_edit, name="teacher_edit"),
    path("teachers/<int:pk>/delete/", views.teacher_delete, name="teacher_delete"),

    # Attendance
    path("attendance/", views.attendance_list, name="attendance_list"),
    path("attendance/add/", views.attendance_create, name="attendance_create"),
    path("attendance/<int:pk>/edit/", views.attendance_edit, name="attendance_edit"),
    path("attendance/<int:pk>/delete/", views.attendance_delete, name="attendance_delete"),

    # Grades
    path("grades/", views.grade_list, name="grade_list"),
    path("grades/add/", views.grade_create, name="grade_create"),
    path("grades/<int:pk>/edit/", views.grade_edit, name="grade_edit"),
    path("grades/<int:pk>/delete/", views.grade_delete, name="grade_delete"),

    # Fee Structures
    path("fees/structures/", views.fee_structure_list, name="fee_structure_list"),
    path("fees/structures/add/", views.fee_structure_create, name="fee_structure_create"),
    path("fees/structures/<int:pk>/edit/", views.fee_structure_edit, name="fee_structure_edit"),
    path("fees/structures/<int:pk>/delete/", views.fee_structure_delete, name="fee_structure_delete"),

    # Fee Invoices
    path("invoices/", views.invoice_list, name="invoice_list"),
    path("invoices/add/", views.invoice_create, name="invoice_create"),
    path("invoices/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("invoices/<int:pk>/edit/", views.invoice_edit, name="invoice_edit"),
    path("invoices/<int:pk>/delete/", views.invoice_delete, name="invoice_delete"),

    # Salaries
    path("salaries/", views.salary_list, name="salary_list"),
    path("salaries/add/", views.salary_create, name="salary_create"),
    path("salaries/<int:pk>/edit/", views.salary_edit, name="salary_edit"),
    path("salaries/<int:pk>/pay/", views.salary_pay, name="salary_pay"),
    path("salaries/<int:pk>/delete/", views.salary_delete, name="salary_delete"),

    # Expenses
    path("expenses/", views.expense_list, name="expense_list"),
    path("expenses/add/", views.expense_create, name="expense_create"),
    path("expenses/<int:pk>/edit/", views.expense_edit, name="expense_edit"),
    path("expenses/<int:pk>/delete/", views.expense_delete, name="expense_delete"),

    # Incomes
    path("incomes/", views.income_list, name="income_list"),
    path("incomes/add/", views.income_create, name="income_create"),
    path("incomes/<int:pk>/edit/", views.income_edit, name="income_edit"),
    path("incomes/<int:pk>/delete/", views.income_delete, name="income_delete"),

    # Donors / Donations
    path("donors/", views.donor_list, name="donor_list"),
    path("donors/add/", views.donor_create, name="donor_create"),
    path("donors/<int:pk>/", views.donor_detail, name="donor_detail"),
    path("donors/<int:pk>/edit/", views.donor_edit, name="donor_edit"),
    path("donors/<int:pk>/delete/", views.donor_delete, name="donor_delete"),

    path("donations/", views.donation_list, name="donation_list"),
    path("donations/add/", views.donation_create, name="donation_create"),
    path("donations/<int:pk>/edit/", views.donation_edit, name="donation_edit"),
    path("donations/<int:pk>/delete/", views.donation_delete, name="donation_delete"),

    # HR
    path("employees/", views.employee_list, name="employee_list"),
    path("employees/add/", views.employee_create, name="employee_create"),
    path("employees/<int:pk>/edit/", views.employee_edit, name="employee_edit"),
    path("employees/<int:pk>/delete/", views.employee_delete, name="employee_delete"),

    path("leaves/", views.leave_list, name="leave_list"),
    path("leaves/add/", views.leave_create, name="leave_create"),
    path("leaves/<int:pk>/edit/", views.leave_edit, name="leave_edit"),
    path("leaves/<int:pk>/decision/<str:decision>/", views.leave_decide, name="leave_decide"),
    path("leaves/<int:pk>/delete/", views.leave_delete, name="leave_delete"),

    # Reports
    path("reports/finance/", views.finance_report, name="finance_report"),
    path("reports/academic/", views.academic_report, name="academic_report"),
    path("emails/", views.sent_emails_log, name="sent_emails_log"),
]
