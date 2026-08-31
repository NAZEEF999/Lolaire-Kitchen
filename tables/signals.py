"""
Signal handlers for the tables app.

Not required this phase: status transitions and soft-delete are both
handled directly in services.py, since they only ever need to react
to actions within this app itself (no cross-app event needs
listening for yet).
"""
