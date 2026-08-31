"""
Django admin registrations for the dashboard app.

Not required: the dashboard has no models of its own to register (see
models.py). Statistics are read live from other apps' models, which
are registered in their own admin.py files.
"""

from django.contrib import admin  # noqa: F401
