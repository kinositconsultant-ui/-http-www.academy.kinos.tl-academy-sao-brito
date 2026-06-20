"""Rebuild the Tailwind CSS bundle (static/css/app.css).

Usage: python manage.py build_tailwind [--watch]

Requires the Tailwind standalone CLI (`tailwindcss`) to be available on PATH.
"""
import subprocess
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Rebuild the Tailwind CSS bundle."

    def add_arguments(self, parser):
        parser.add_argument("--watch", action="store_true",
                            help="Watch templates and rebuild on change.")

    def handle(self, *args, **opts):
        base = Path(settings.BASE_DIR)
        cfg = base / "tailwind.config.js"
        src = base / "static" / "css" / "tailwind.src.css"
        out = base / "static" / "css" / "app.css"
        cmd = ["tailwindcss", "-c", str(cfg), "-i", str(src), "-o", str(out), "--minify"]
        if opts["watch"]:
            cmd.append("--watch")
        self.stdout.write(self.style.NOTICE(f"Running: {' '.join(cmd)}"))
        subprocess.run(cmd, check=True, cwd=str(base))
        self.stdout.write(self.style.SUCCESS(f"Wrote {out}"))
