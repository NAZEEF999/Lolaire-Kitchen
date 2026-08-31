"""
Django admin registrations for the reports app.

Not required: reports has no models of its own to register (see
models.py) — it's a read-only analytics layer over other apps' data,
which are registered in their own admin.py files.
"""

from django.contrib import admin  # noqa: F401
