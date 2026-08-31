"""
Models for the reports app.

Reports is a pure read-only analytics layer over data owned by other
apps (orders, menu, customers, tables) — it has no database tables of
its own, mirroring the same design as the dashboard app. No models,
and therefore no QuerySet-backed managers, are needed here.
"""

from django.db import models  # noqa: F401
from core.models import TimeStampedModel  # noqa: F401
