"""
Signal handlers for the menu app.

Not required this phase: slug generation and the soft-delete cascade
are both handled directly in models.py/services.py, since they only
ever need to react to actions within this app itself (no cross-app
event needs listening for yet).
"""
