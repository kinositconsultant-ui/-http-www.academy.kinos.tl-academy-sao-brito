"""Parent portal, Stripe online payments, and bulk PDF report cards."""
import io
import zipfile
from asgiref.sync import sync_to_async

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseRedirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db.models import Sum
from django.urls import reverse

from accounts.models import School
from .models import (
    Student, SchoolClass, FeeInvoice, FeePayment, Income, Grade,
    AcademicYear, PaymentTransaction,
)
from .report_card import build_report_card


# =====================================================================
# Parent portal
# =====================================================================

def _parent_only(user):
    return user.is_authenticated and (user.role == "parent" or user.is_superuser)


@login_required
def parent_dashboard(request):
    """Landing page for parents — lists all linked children with quick stats."""
    if not _parent_only(request.user):
        return redirect("dashboard")
    children = request.user.children.select_related("school_class").filter(is_active=True)
    rows = []
    for c in children:
        outstanding = c.invoices.exclude(status="paid").aggregate(
            amt=Sum("amount"), paid=Sum("amount_paid"))
        balance = (outstanding["amt"] or 0) - (outstanding["paid"] or 0)
        latest_grades = c.grades.select_related("subject").order_by("-recorded_at")[:3]
        rows.append({"student": c, "balance": balance, "grades": latest_grades})
    from .academy_views import today_widget_context
    return render(request, "erp/parent_dashboard.html", {
        "rows": rows,
        **today_widget_context(request.user),
    })


@login_required
def parent_student_detail(request, pk):
    """Detailed view of a single child for the logged-in parent."""
    student = get_object_or_404(Student, pk=pk)
    if not _parent_only(request.user) or not student.parent_users.filter(id=request.user.id).exists():
        if not request.user.is_superuser:
            return HttpResponseForbidden("Not your child.")
    invoices = student.invoices.all()
    grades = student.grades.select_related("subject", "academic_year").order_by("-recorded_at")[:50]
    attendance = student.attendance.order_by("-date")[:30]
    evaluations = student.evaluations.filter(visible_to_parent=True).select_related(
        "teacher", "academic_year").order_by("-created_at")
    years = AcademicYear.objects.all()
    return render(request, "erp/parent_student.html", {
        "student": student, "invoices": invoices,
        "grades": grades, "attendance": attendance, "years": years,
        "evaluations": evaluations,
        "current_year": AcademicYear.objects.filter(is_current=True).first(),
    })


# =====================================================================
# Bulk PDF report cards (one ZIP per class)
# =====================================================================

@login_required
def class_report_cards_zip(request, class_id):
    cl = get_object_or_404(SchoolClass, pk=class_id)
    year_id = request.GET.get("year")
    year = AcademicYear.objects.filter(id=year_id).first() if year_id else (
        AcademicYear.objects.filter(is_current=True).first())

    students = cl.students.filter(is_active=True)
    school = School.get_active()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for s in students:
            grades_qs = s.grades.select_related("subject", "academic_year")
            if year:
                grades_qs = grades_qs.filter(academic_year=year)
            grades = list(grades_qs.order_by("subject__name", "semester"))
            att = s.attendance.all()
            if year:
                att = att.filter(date__gte=year.start_date, date__lte=year.end_date)
            stats = {"present": att.filter(status="present").count(),
                     "total": att.count()}
            pdf = build_report_card(student=s, grades=grades, school=school,
                                    academic_year=year, attendance_stats=stats)
            safe = s.full_name.replace(" ", "_")
            zf.writestr(f"report-card_{safe}_{s.admission_no}.pdf", pdf)

    buf.seek(0)
    year_label = year.name if year else "all-years"
    safe_cl = str(cl).replace(" ", "_").replace("/", "-")
    response = HttpResponse(buf.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = (
        f'attachment; filename="report-cards_{safe_cl}_{year_label}.zip"'
    )
    return response


# =====================================================================
# Stripe online fee payment
# =====================================================================

def _get_stripe_checkout(request):
    """Build a StripeCheckout client using the host URL for the webhook (sync helper, unused after async refactor)."""
    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    api_key = settings.STRIPE_API_KEY
    host_url = f"{request.scheme}://{request.get_host()}"
    webhook_url = f"{host_url}/api/webhook/stripe"
    return StripeCheckout(api_key=api_key, webhook_url=webhook_url)


async def invoice_pay_online(request, pk):
    """Create a Stripe Checkout session for the invoice's outstanding balance."""
    user = await request.auser()
    if not user.is_authenticated:
        return HttpResponseRedirect("/api/login/")
    if request.method != "POST":
        return HttpResponse(status=405)
    invoice = await sync_to_async(get_object_or_404)(FeeInvoice, pk=pk)
    if invoice.status == "paid" or invoice.balance <= 0:
        await sync_to_async(messages.info)(request, "This invoice is already fully paid.")
        return HttpResponseRedirect(f"/api/invoices/{invoice.pk}/")

    amount = float(invoice.balance)
    student = await sync_to_async(lambda: invoice.student)()

    host_url = f"{request.scheme}://{request.get_host()}"
    success_url = f"{host_url}/api/invoices/{invoice.pk}/?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{host_url}/api/invoices/{invoice.pk}/"

    from emergentintegrations.payments.stripe.checkout import (
        StripeCheckout, CheckoutSessionRequest,
    )
    checkout = StripeCheckout(
        api_key=settings.STRIPE_API_KEY,
        webhook_url=f"{host_url}/api/webhook/stripe",
    )
    req = CheckoutSessionRequest(
        amount=amount, currency="usd",
        success_url=success_url, cancel_url=cancel_url,
        metadata={
            "invoice_id": str(invoice.pk),
            "student_admission": student.admission_no,
            "user_id": str(user.id),
            "source": "academy_erp_invoice",
        },
    )

    session = None
    try:
        session = await checkout.create_checkout_session(req)
    except Exception as exc:  # noqa: BLE001
        import traceback
        print(f"[stripe checkout error] {exc!r}")
        traceback.print_exc()
        await sync_to_async(messages.error)(
            request, f"Could not start Stripe checkout: {exc}")
        return HttpResponseRedirect(f"/api/invoices/{invoice.pk}/")

    await sync_to_async(PaymentTransaction.objects.create)(
        invoice=invoice, session_id=session.session_id,
        amount=amount, currency="usd", status="initiated",
        metadata=dict(req.metadata or {}),
        initiated_by=user,
    )
    return HttpResponseRedirect(session.url)


async def invoice_pay_crypto(request, pk):
    """Create a Stripe Checkout session for crypto payment.

    Note: Stripe Checkout displays crypto as a payment method when it's enabled
    in your Stripe Dashboard (Settings → Payment methods → Crypto). When using
    the emergentintegrations proxy, the merchant's underlying Stripe account
    controls whether crypto appears on the hosted checkout. The button below
    creates the same Checkout session and tags it `method=crypto` for audit.
    """
    user = await request.auser()
    if not user.is_authenticated:
        return HttpResponseRedirect("/api/login/")
    if request.method != "POST":
        return HttpResponse(status=405)
    if not settings.STRIPE_ENABLE_CRYPTO:
        return HttpResponseRedirect(f"/api/invoices/{pk}/")

    invoice = await sync_to_async(get_object_or_404)(FeeInvoice, pk=pk)
    if invoice.status == "paid" or invoice.balance <= 0:
        return HttpResponseRedirect(f"/api/invoices/{invoice.pk}/")

    amount = float(invoice.balance)
    student = await sync_to_async(lambda: invoice.student)()

    host_url = f"{request.scheme}://{request.get_host()}"
    success_url = f"{host_url}/api/invoices/{invoice.pk}/?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{host_url}/api/invoices/{invoice.pk}/"

    from emergentintegrations.payments.stripe.checkout import (
        StripeCheckout, CheckoutSessionRequest,
    )
    checkout = StripeCheckout(
        api_key=settings.STRIPE_API_KEY,
        webhook_url=f"{host_url}/api/webhook/stripe",
    )
    req = CheckoutSessionRequest(
        amount=amount, currency="usd",
        success_url=success_url, cancel_url=cancel_url,
        metadata={
            "invoice_id": str(invoice.pk),
            "student_admission": student.admission_no,
            "user_id": str(user.id),
            "source": "academy_erp_invoice_crypto",
            "method": "crypto",
        },
    )

    session = None
    try:
        session = await checkout.create_checkout_session(req)
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        await sync_to_async(messages.error)(
            request, f"Could not start crypto checkout: {exc}")
        return HttpResponseRedirect(f"/api/invoices/{invoice.pk}/")

    await sync_to_async(PaymentTransaction.objects.create)(
        invoice=invoice, session_id=session.session_id,
        amount=amount, currency="usd", status="initiated",
        metadata=dict(req.metadata or {}),
        initiated_by=user,
    )
    return HttpResponseRedirect(session.url)


async def invoice_payment_status(request, pk):
    """Polling endpoint used by JS after returning from Stripe."""
    user = await request.auser()
    if not user.is_authenticated:
        return JsonResponse({"error": "unauthorized"}, status=401)
    invoice = await sync_to_async(get_object_or_404)(FeeInvoice, pk=pk)
    session_id = request.GET.get("session_id")
    if session_id:
        tx = await sync_to_async(
            lambda: PaymentTransaction.objects.filter(invoice=invoice, session_id=session_id).first()
        )()
    else:
        tx = await sync_to_async(
            lambda: PaymentTransaction.objects.filter(invoice=invoice).order_by("-created_at").first()
        )()
    if not tx:
        return JsonResponse({"error": "no_transaction"}, status=404)

    if tx.status == "paid":
        return JsonResponse({"payment_status": "paid", "status": "complete"})

    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    host_url = f"{request.scheme}://{request.get_host()}"
    checkout = StripeCheckout(
        api_key=settings.STRIPE_API_KEY,
        webhook_url=f"{host_url}/api/webhook/stripe",
    )
    live = None
    try:
        live = await checkout.get_checkout_status(tx.session_id)
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"error": str(exc)}, status=500)

    tx.payment_status = live.payment_status or ""
    if live.payment_status == "paid" and tx.status != "paid":
        tx.status = "paid"
        await sync_to_async(tx.save)()
        await sync_to_async(_settle_invoice)(invoice, tx)
    elif live.status == "expired":
        tx.status = "expired"
        await sync_to_async(tx.save)()
    else:
        tx.status = "pending"
        await sync_to_async(tx.save)()

    return JsonResponse({
        "payment_status": live.payment_status,
        "status": live.status,
        "invoice_status": invoice.status,
    })


def _settle_invoice(invoice, tx):
    """Idempotent: create FeePayment + Income for this transaction once."""
    if FeePayment.objects.filter(reference=tx.session_id).exists():
        return
    payment = FeePayment.objects.create(
        invoice=invoice, amount=tx.amount, method="card",
        reference=tx.session_id, paid_on=timezone.now().date(),
        received_by=tx.initiated_by,
    )
    invoice.amount_paid = invoice.payments.aggregate(s=Sum("amount"))["s"] or 0
    invoice.refresh_status()
    invoice.save()
    Income.objects.create(
        title=f"Stripe online payment - {invoice.student.full_name}",
        source="fees", amount=payment.amount, date=payment.paid_on,
        note=f"Invoice #{invoice.id} (Stripe session {tx.session_id[:14]}…)",
    )
    # Email receipt
    try:
        from .mail import send_email, render_payment_receipt
        to = invoice.student.parent_email
        if to:
            send_email(
                to_email=to,
                subject=f"Payment receipt - Invoice #{invoice.id}",
                html=render_payment_receipt(invoice, payment, School.get_active()),
                related_invoice=invoice,
            )
    except Exception as exc:  # noqa: BLE001
        print(f"[receipt] failed to dispatch: {exc}")


@csrf_exempt
async def stripe_webhook(request):
    """Stripe webhook receiver — settles invoices when checkout.session.completed."""
    if request.method != "POST":
        return HttpResponse(status=405)
    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    host_url = f"{request.scheme}://{request.get_host()}"
    checkout = StripeCheckout(
        api_key=settings.STRIPE_API_KEY,
        webhook_url=f"{host_url}/api/webhook/stripe",
    )
    try:
        evt = await checkout.handle_webhook(
            request.body, request.headers.get("Stripe-Signature", ""))
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"error": str(exc)}, status=400)

    if evt.session_id:
        tx = await sync_to_async(
            lambda: PaymentTransaction.objects.filter(session_id=evt.session_id).first()
        )()
        if tx:
            tx.payment_status = evt.payment_status or ""
            if evt.payment_status == "paid" and tx.status != "paid":
                tx.status = "paid"
                await sync_to_async(tx.save)()
                invoice = await sync_to_async(lambda: tx.invoice)()
                await sync_to_async(_settle_invoice)(invoice, tx)
            else:
                await sync_to_async(tx.save)()
    return JsonResponse({"ok": True})
