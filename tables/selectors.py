"""
Database query logic for the tables app.

Read-only helpers used by views and services. Keeps ORM query
construction out of views.py.
"""

from .models import Table, TableStatus


def get_tables(*, status=None):
    """Active tables, optionally filtered by status."""
    queryset = Table.objects.all()
    if status:
        queryset = queryset.filter(status=status)
    return queryset


def get_table_by_id(table_id):
    return Table.objects.filter(pk=table_id).first()


def get_table_by_number(table_number):
    return Table.objects.filter(table_number=table_number).first()


def get_available_tables():
    return Table.objects.filter(status=TableStatus.AVAILABLE)


def get_occupied_tables():
    return Table.objects.filter(status=TableStatus.OCCUPIED)
