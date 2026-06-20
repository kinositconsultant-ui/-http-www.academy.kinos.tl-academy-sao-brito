"""SendGrid email sender.

If SENDGRID_API_KEY and SENDGRID_FROM_EMAIL are set in the environment, real
emails are sent via the official SendGrid SDK. Otherwise emails are written
to the SentEmail audit log + stdout so receipts are visible end-to-end while
running in MOCK mode.

To enable real sending, set in /app/backend/.env:
    SENDGRID_API_KEY=SG.xxxxxxxxxxxx
    SENDGRID_FROM_EMAIL=no-reply@isjb.edu   (must be verified in SendGrid)
"""
import os
from django.utils import timezone


def _is_live():
    return bool(os.environ.get("SENDGRID_API_KEY")) and bool(os.environ.get("SENDGRID_FROM_EMAIL"))


def _send_via_sdk(to_email: str, subject: str, html: str):
    """Real send via official sendgrid SDK. Returns (ok, error_text)."""
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    try:
        msg = Mail(
            from_email=os.environ["SENDGRID_FROM_EMAIL"],
            to_emails=to_email,
            subject=subject,
            html_content=html,
        )
        sg = SendGridAPIClient(os.environ["SENDGRID_API_KEY"])
        resp = sg.send(msg)
        ok = resp.status_code in (200, 202)
        if not ok:
            return False, f"HTTP {resp.status_code}: {getattr(resp, 'body', '')!s:.200}"
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def send_email(to_email: str, subject: str, html: str, *, related_invoice=None):
    """Send an email. Returns a dict with status info.

    Always records a SentEmail row regardless of mock/live mode.
    """
    from .models import SentEmail  # local import to avoid circular

    if not to_email:
        return {"status": "skipped", "reason": "no recipient"}

    mode = "live" if _is_live() else "mock"
    if mode == "live":
        ok, error_text = _send_via_sdk(to_email, subject, html)
    else:
        ok, error_text = True, ""
        print(f"[SendGrid MOCK] To: {to_email} | Subject: {subject}\n"
              f"--- HTML ---\n{html}\n--- END ---")

    SentEmail.objects.create(
        to_email=to_email, subject=subject, html=html, mode=mode,
        success=ok, error=error_text, invoice=related_invoice,
        sent_at=timezone.now(),
    )
    return {"status": "sent" if ok else "failed", "mode": mode, "error": error_text}


def render_payment_receipt(invoice, payment, school) -> str:
    """Tiny HTML template for a payment receipt."""
    currency = (school.currency if school else "USD") or "USD"
    return f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 520px; margin: 0 auto;
                padding: 24px; border: 1px solid #e4e4e7; border-radius: 8px;">
      <div style="border-bottom: 2px solid #2563eb; padding-bottom: 12px; margin-bottom: 16px;">
        <h2 style="margin: 0; color: #18181b; font-size: 18px;">{school.name if school else 'Academy ERP'}</h2>
        <div style="color: #71717a; font-size: 12px; text-transform: uppercase; letter-spacing: 0.1em;">Payment Receipt</div>
      </div>
      <p style="margin: 0 0 8px; color: #52525b;">Dear {invoice.student.father_name or invoice.student.parent_email or 'Parent'},</p>
      <p style="margin: 0 0 16px; color: #52525b;">We confirm receipt of your payment for the following invoice:</p>
      <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
        <tr><td style="padding: 4px 0; color: #71717a;">Student:</td><td style="padding: 4px 0; font-weight: 600;">{invoice.student.full_name}</td></tr>
        <tr><td style="padding: 4px 0; color: #71717a;">Invoice #:</td><td style="padding: 4px 0; font-family: monospace;">#{invoice.id}</td></tr>
        <tr><td style="padding: 4px 0; color: #71717a;">Title:</td><td style="padding: 4px 0;">{invoice.title}</td></tr>
        <tr><td style="padding: 4px 0; color: #71717a;">Amount paid:</td><td style="padding: 4px 0; font-weight: 700; color: #047857;">{currency} {payment.amount:.2f}</td></tr>
        <tr><td style="padding: 4px 0; color: #71717a;">Method:</td><td style="padding: 4px 0;">{payment.get_method_display()}</td></tr>
        <tr><td style="padding: 4px 0; color: #71717a;">Date:</td><td style="padding: 4px 0;">{payment.paid_on}</td></tr>
        <tr><td style="padding: 4px 0; color: #71717a;">Outstanding balance:</td><td style="padding: 4px 0; font-weight: 600;">{currency} {invoice.balance:.2f}</td></tr>
      </table>
      <p style="margin: 16px 0 0; color: #71717a; font-size: 12px;">
        Thank you for your payment. This is an automated receipt — please retain for your records.
      </p>
    </div>
    """
