"""
Reusable helper functions for the tables app.
"""


def format_table_label(table):
    """
    Build a compact, human-readable label for a table, e.g.
    "Table 5 (Patio)" or just "Table 5" if no location is set.
    """
    label = table.name or f"Table {table.table_number}"
    if table.location:
        label = f"{label} ({table.location})"
    return label
