"""
Models for the dashboard app.

The dashboard is a pure aggregation/reporting layer — it reads data
that lives in the customers, menu, orders, and tables apps via
selectors.py and has no database tables of its own. No models are
defined here by design.
"""

from django.db import models  # noqa: F401
from core.models import TimeStampedModel  # noqa: F401
