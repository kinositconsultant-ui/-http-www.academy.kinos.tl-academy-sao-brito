from django.urls import path
from django.views.generic import RedirectView
from . import views
from . import portal_views
from . import student_views
from . import hr_views
from . import teacher_views

urlpatterns = [
    path("", RedirectView.as_view(url="/api/dashboard/", permanent=False)),
    path("dashboard/", views.dashboard, name="dashboard"),

    # Teacher portal
    path("teacher/", teacher_views.teacher_dashboard, name="teacher_dashboard"),
    path("teacher/attendance/", teacher_views.teacher_attendance, name="teacher_attendance"),
    path("teacher/grades/", teacher_views.teacher_grades, name="teacher_grades"),
    path("teacher/evaluations/", teacher_views.teacher_evaluations, name="teacher_evaluations"),
    path("teacher/evaluations/add/", teacher_views.teacher_evaluation_add, name="teacher_evaluation_add"),
    path("teacher/evaluations/<int:pk>/delete/", teacher_views.teacher_evaluation_delete, name="teacher_evaluation_delete"),
    path("teacher/profile/", teacher_views.teacher_profile, name="teacher_profile"),
    path("teacher/leave/", teacher_views.teacher_leave_request, name="teacher_leave_request"),
    path("teachers/<int:pk>/create-login/", teacher_views.create_teacher_login, name="teacher_create_login"),

    # HR module
    path("hr/", hr_views.hr_dashboard, name="hr_dashboard"),
    path("hr/jobs/", hr_views.job_list, name="hr_job_list"),
    path("hr/jobs/add/", hr_views.job_add, name="hr_job_add"),
    path("hr/jobs/<int:pk>/delete/", hr_views.job_delete, name="hr_job_delete"),
    path("hr/candidates/", hr_views.candidate_list, name="hr_candidate_list"),
    path("hr/candidates/add/", hr_views.candidate_add, name="hr_candidate_add"),
    path("hr/candidates/<int:pk>/delete/", hr_views.candidate_delete, name="hr_candidate_delete"),
    path("hr/training/", hr_views.training_list, name="hr_training_list"),
    path("hr/training/add/", hr_views.training_add, name="hr_training_add"),
    path("hr/training/<int:pk>/delete/", hr_views.training_delete, name="hr_training_delete"),
    path("hr/enrollments/", hr_views.enrollment_list, name="hr_enrollment_list"),
    path("hr/enrollments/add/", hr_views.enrollment_add, name="hr_enrollment_add"),
    path("hr/enrollments/<int:pk>/delete/", hr_views.enrollment_delete, name="hr_enrollment_delete"),
    path("hr/reviews/", hr_views.review_list, name="hr_review_list"),
    path("hr/reviews/add/", hr_views.review_add, name="hr_review_add"),
    path("hr/reviews/<int:pk>/delete/", hr_views.review_delete, name="hr_review_delete"),
    path("hr/employee-attendance/", hr_views.employee_attendance_list, name="hr_employee_attendance_list"),
    path("hr/employee-attendance/add/", hr_views.employee_attendance_add, name="hr_employee_attendance_add"),
    path("hr/employee-attendance/<int:pk>/delete/", hr_views.employee_attendance_delete, name="hr_employee_attendance_delete"),
    path("hr/inventory/", hr_views.inventory_list, name="hr_inventory_list"),
    path("hr/inventory/add/", hr_views.inventory_add, name="hr_inventory_add"),
    path("hr/inventory/categories/add/", hr_views.category_add, name="hr_inventory_category_add"),
    path("hr/inventory/<int:pk>/delete/", hr_views.inventory_delete, name="hr_inventory_delete"),
    path("hr/assignments/", hr_views.assignment_list, name="hr_assignment_list"),
    path("hr/assignments/add/", hr_views.assignment_add, name="hr_assignment_add"),
    path("hr/assignments/<int:pk>/delete/", hr_views.assignment_delete, name="hr_assignment_delete"),
    path("hr/payslip/<int:pk>.pdf", hr_views.payslip_pdf, name="hr_payslip_pdf"),

    # Parent portal
    path("parent/", portal_views.parent_dashboard, name="parent_dashboard"),
    path("parent/student/<int:pk>/", portal_views.parent_student_detail, name="parent_student_detail"),

    # Student portal
    path("student/", student_views.student_dashboard, name="student_dashboard"),
    path("student/grades/", student_views.student_grades, name="student_grades"),
    path("student/subjects/", student_views.student_subjects, name="student_subjects"),
    path("student/credits/", student_views.student_credits, name="student_credits"),
    path("student/invoices/", student_views.student_invoices, name="student_invoices"),
    path("student/report-card/", student_views.student_report_card, name="student_report_card_self"),

    # Admin action: create student login
    path("students/<int:pk>/create-login/", student_views.create_student_login, name="student_create_login"),

    # Credit notes (admin/accountant)
    path("credit-notes/", student_views.credit_note_list, name="credit_note_list"),
    path("credit-notes/add/", student_views.credit_note_create, name="credit_note_create"),
    path("credit-notes/<int:pk>/delete/", student_views.credit_note_delete, name="credit_note_delete"),

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
    path("invoices/<int:pk>/pdf/", views.invoice_pdf, name="invoice_pdf"),
    path("payments/<int:pk>/receipt.pdf", views.payment_receipt_pdf, name="payment_receipt_pdf"),

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
