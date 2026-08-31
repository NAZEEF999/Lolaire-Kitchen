"""
Tests for the core app.
"""

from django.test import TestCase

from core.models import TimeStampedModel


class TimeStampedModelTests(TestCase):
    def test_is_abstract(self):
        self.assertTrue(TimeStampedModel._meta.abstract)
