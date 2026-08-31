"""
Database query logic for the accounts app.

Read-only helpers used by views, services, and other apps. Keeps ORM
query construction out of views.py.
"""

from django.contrib.auth import get_user_model

from .models import UserRole

User = get_user_model()


def get_user_by_username(username):
    return User.objects.filter(username=username).first()


def get_active_users():
    return User.objects.filter(is_active=True)


def get_users_by_role(role):
    return User.objects.filter(role=role, is_active=True)


def get_administrators():
    return get_users_by_role(UserRole.ADMINISTRATOR)


def get_managers():
    return get_users_by_role(UserRole.MANAGER)


def get_cashiers():
    return get_users_by_role(UserRole.CASHIER)


def get_waiters():
    return get_users_by_role(UserRole.WAITER)
