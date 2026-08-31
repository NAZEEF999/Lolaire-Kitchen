"""
Reusable helper functions for the reports app.
"""


def as_export_rows(queryset_or_list, fields):
    """
    Flatten a queryset/list of objects into plain dict rows keyed by
    `fields`. Kept generic and format-agnostic so a future PDF/Excel
    export can reuse it — not wired to any export library yet.
    """
    rows = []
    for obj in queryset_or_list:
        if isinstance(obj, dict):
            rows.append({field: obj.get(field) for field in fields})
        else:
            rows.append({field: getattr(obj, field, None) for field in fields})
    return rows
