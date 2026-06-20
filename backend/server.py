"""ASGI entry point for supervisor.

Supervisor runs: uvicorn server:app --host 0.0.0.0 --port 8001
We expose Django's ASGI application as `app`.
"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "academy_erp.settings")

from django.core.asgi import get_asgi_application  # noqa: E402

app = get_asgi_application()
