"""
Vercel's Python runtime auto-detects a WSGI-compatible callable named
`app` in this file and routes every request from vercel.json here.
This is the only thing this file does — the actual Django project
(settings, urls, apps) is entirely untouched and lives where it
always has, at the project root.
"""
import os
import sys
from pathlib import Path

# Make the project root importable — this file lives in api/, one
# level below manage.py, core/, accounts/, etc.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

app = get_wsgi_application()
