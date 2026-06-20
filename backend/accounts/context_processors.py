from django.conf import settings
from .models import School


def school_context(request):
    return {
        "school": School.get_active(),
        "stripe_crypto_enabled": getattr(settings, "STRIPE_ENABLE_CRYPTO", False),
    }
