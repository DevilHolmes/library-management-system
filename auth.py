"""
auth.py - Authentication & Role-Based Access Control

Provides:
  - hash_password / verify_password  : bcrypt-style hashing via hashlib
  - PERMISSIONS                      : role → frozenset of allowed actions
  - has_permission                   : predicate check
  - require_permission               : decorator for LibrarySystem methods
"""

import hashlib
import hmac
import os
import functools
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from models import User


# ── Password Hashing (SHA-256 + salt, no external deps) ───────────────────────

def hash_password(password: str) -> str:
    """Return a salted SHA-256 hash as 'salt$hash' (hex-encoded)."""
    salt = os.urandom(16).hex()
    digest = hmac.new(salt.encode(), password.encode(), hashlib.sha256).hexdigest()
    return f"{salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Return True if password matches the stored 'salt$hash'."""
    try:
        salt, digest = stored_hash.split("$", 1)
        expected = hmac.new(salt.encode(), password.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, digest)
    except (ValueError, AttributeError):
        return False


# ── Permission Table ──────────────────────────────────────────────────────────

_ADMIN_PERMISSIONS = frozenset({
    # User management
    "create_user", "delete_user", "view_all_users", "update_any_user",
    # Book management
    "add_book", "delete_book", "update_book", "view_all_books", "view_inventory",
    # Circulation
    "borrow_book", "return_book", "process_return", "reserve_book",
    # Fines
    "waive_fine", "collect_fine",
    # Reports & Analytics
    "view_reports", "generate_reports", "view_borrow_history",
    # Logs & Audit
    "view_logs",
    # Notifications
    "send_notifications",
    # Data management
    "backup_data", "restore_data",
    # Registration approval
    "approve_registration", "reject_registration",
    # Config
    "manage_config",
})

_STAFF_PERMISSIONS = frozenset({
    # User management (limited)
    "view_all_users",
    # Book management
    "add_book", "delete_book", "update_book", "view_all_books", "view_inventory",
    # Circulation
    "borrow_book", "return_book", "process_return", "reserve_book",
    # Fines
    "collect_fine",
    # Reports
    "view_reports", "view_borrow_history",
    # Logs
    "view_logs",
    # Notifications
    "send_notifications",
    # Registration approval
    "approve_registration", "reject_registration", "create_user",
})

_USER_PERMISSIONS = frozenset({
    "borrow_book", "return_book", "reserve_book",
    "view_all_books", "view_inventory",
})

PERMISSIONS: dict = {
    "admin": _ADMIN_PERMISSIONS,
    "staff": _STAFF_PERMISSIONS,
    "user":  _USER_PERMISSIONS,
}


# ── Public Helpers ────────────────────────────────────────────────────────────

def has_permission(user: "User", action: str) -> bool:
    """Return True if user's role grants the named action."""
    role_perms = PERMISSIONS.get(user.role.value, frozenset())
    return action in role_perms


def require_permission(action: str) -> Callable:
    """
    Decorator for LibrarySystem methods.
    The first argument after `self` must be the acting User (current_user).

    Usage:
        @require_permission("add_book")
        def add_book(self, current_user: User, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, current_user: "User", *args, **kwargs):
            if not has_permission(current_user, action):
                raise PermissionError(
                    f"🚫 '{current_user.role.value.upper()}' does not have "
                    f"permission to '{action}'."
                )
            return func(self, current_user, *args, **kwargs)
        return wrapper
    return decorator
