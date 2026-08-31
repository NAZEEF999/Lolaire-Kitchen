"""
Business logic for the tables app.

Views call into this module for anything that writes to the database,
keeping views.py lightweight per the project's BUSINESS LOGIC rule.
Status changes go exclusively through change_table_status() — the
single path for status transitions, per the project's business rules.
"""

from django.core.exceptions import ValidationError

from .models import Table, TableStatus


def create_table(*, table_number, capacity, name="", location="", notes="", is_active=True):
    """
    New tables always start Available — status is deliberately not a
    parameter here; use change_table_status() afterward if a different
    starting status is needed.
    """
    return Table.objects.create(
        table_number=table_number,
        name=name,
        capacity=capacity,
        status=TableStatus.AVAILABLE,
        location=location,
        notes=notes,
        is_active=is_active,
    )


def update_table(*, table, table_number=None, name=None, capacity=None, location=None, notes=None, is_active=None):
    """
    Update a table's structural fields. Only the fields explicitly
    passed (not None) are changed. Status is intentionally not
    accepted here — see change_table_status().
    """
    fields_to_update = []

    if table_number is not None:
        table.table_number = table_number
        fields_to_update.append("table_number")
    if name is not None:
        table.name = name
        fields_to_update.append("name")
    if capacity is not None:
        table.capacity = capacity
        fields_to_update.append("capacity")
    if location is not None:
        table.location = location
        fields_to_update.append("location")
    if notes is not None:
        table.notes = notes
        fields_to_update.append("notes")
    if is_active is not None:
        table.is_active = is_active
        fields_to_update.append("is_active")

    if fields_to_update:
        fields_to_update.append("updated_at")
        table.save(update_fields=fields_to_update)

    return table


def change_table_status(*, table, new_status):
    """The single path for changing a table's status."""
    if new_status not in TableStatus.values:
        raise ValidationError(f"'{new_status}' is not a valid table status.")
    table.status = new_status
    table.save(update_fields=["status", "updated_at"])
    return table


def deactivate_table(*, table):
    """
    Soft-delete a table. Occupied tables cannot be deleted — free the
    table up (change its status away from Occupied) first.
    """
    if table.status == TableStatus.OCCUPIED:
        raise ValidationError("An occupied table cannot be deleted. Change its status first.")
    table.is_active = False
    table.save(update_fields=["is_active", "updated_at"])
    return table
