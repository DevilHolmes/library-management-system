"""
config.py - System-wide Configuration for the Library Management System

All tuneable constants live here. Import with:
    from config import config
    print(config.FINE_PER_DAY)

The Config object can be serialised/deserialised so admins can persist
changes across restarts via save_config() / load_config().
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List


@dataclass
class Config:
    # ── Borrowing Rules ───────────────────────────────────────────────────────
    BORROW_DURATION_DAYS: int = 14        # standard loan period
    MAX_BOOKS_USER: int = 3               # max concurrent borrows for USER role
    MAX_BOOKS_STAFF: int = 10             # max concurrent borrows for STAFF role
    MAX_BOOKS_ADMIN: int = 10             # max concurrent borrows for ADMIN role
    RESERVATION_EXPIRY_HOURS: int = 48   # how long a reservation is held

    # ── Fine Policy ───────────────────────────────────────────────────────────
    FINE_PER_DAY: float = 5.0            # ₹ per overdue day
    FINE_GRACE_DAYS: int = 0             # grace days before fine kicks in
    MAX_FINE_PER_RECORD: float = 500.0   # cap per borrow record (0 = no cap)

    # ── Password Policy ───────────────────────────────────────────────────────
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPER: bool = True
    PASSWORD_REQUIRE_LOWER: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = False
    PASSWORD_SPECIAL_CHARS: str = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    # ── Session Policy ────────────────────────────────────────────────────────
    SESSION_TIMEOUT_MINUTES: int = 60    # 0 = never expire
    MAX_SESSIONS_PER_USER: int = 3       # 0 = unlimited

    # ── Notification Settings ─────────────────────────────────────────────────
    NOTIFY_ON_BORROW: bool = True
    NOTIFY_ON_RETURN: bool = True
    NOTIFY_ON_OVERDUE: bool = True
    NOTIFY_DUE_REMINDER_DAYS: int = 3    # send reminder N days before due
    NOTIFY_VERBOSE: bool = True          # print to console

    # ── Search Settings ───────────────────────────────────────────────────────
    SEARCH_MAX_RESULTS: int = 100
    SEARCH_CASE_SENSITIVE: bool = False

    # ── Report Settings ───────────────────────────────────────────────────────
    REPORT_TOP_N: int = 10               # default "top N" for rankings
    REPORTS_DIR: str = "reports"         # directory for exported reports

    # ── Import / Export ───────────────────────────────────────────────────────
    IMPORT_SKIP_DUPLICATES: bool = True  # skip rows with duplicate ISBN on import
    EXPORT_DATE_FORMAT: str = "%Y-%m-%d"
    CSV_DELIMITER: str = ","

    # ── Maintenance ───────────────────────────────────────────────────────────
    SAVE_FILE: str = "library_data.json"
    AUTO_SAVE_ON_EXIT: bool = True
    LOG_MAX_ENTRIES: int = 10_000        # trim audit log if it exceeds this

    # ── Library Identity ──────────────────────────────────────────────────────
    LIBRARY_NAME: str = "City Public Library"
    LIBRARY_EMAIL: str = "library@city.gov"
    LIBRARY_PHONE: str = "+91-000-000-0000"
    LIBRARY_ADDRESS: str = ""
    CURRENCY_SYMBOL: str = "₹"

    def display(self):
        """Pretty-print all configuration values."""
        print(f"\n{'═'*60}")
        print("  ⚙️   SYSTEM CONFIGURATION")
        print(f"{'═'*60}")
        sections = {
            "Borrowing Rules":      ["BORROW_DURATION_DAYS","MAX_BOOKS_USER","MAX_BOOKS_STAFF","MAX_BOOKS_ADMIN","RESERVATION_EXPIRY_HOURS"],
            "Fine Policy":          ["FINE_PER_DAY","FINE_GRACE_DAYS","MAX_FINE_PER_RECORD"],
            "Password Policy":      ["PASSWORD_MIN_LENGTH","PASSWORD_REQUIRE_UPPER","PASSWORD_REQUIRE_LOWER","PASSWORD_REQUIRE_DIGIT","PASSWORD_REQUIRE_SPECIAL"],
            "Session Policy":       ["SESSION_TIMEOUT_MINUTES","MAX_SESSIONS_PER_USER"],
            "Notifications":        ["NOTIFY_ON_BORROW","NOTIFY_ON_RETURN","NOTIFY_ON_OVERDUE","NOTIFY_DUE_REMINDER_DAYS","NOTIFY_VERBOSE"],
            "Reports & Export":     ["REPORT_TOP_N","REPORTS_DIR","EXPORT_DATE_FORMAT"],
            "Library Identity":     ["LIBRARY_NAME","LIBRARY_EMAIL","LIBRARY_PHONE","CURRENCY_SYMBOL"],
        }
        for section, keys in sections.items():
            print(f"\n  ── {section}")
            for k in keys:
                val = getattr(self, k)
                print(f"    {k:<35}: {val}")
        print(f"\n{'═'*60}\n")

    def update(self, **kwargs):
        """Update one or more settings at runtime."""
        for key, value in kwargs.items():
            if not hasattr(self, key):
                raise ValueError(f"Unknown config key: '{key}'")
            expected = type(getattr(self, key))
            try:
                setattr(self, key, expected(value))
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid value for '{key}': {e}")

    def max_books_for_role(self, role) -> int:
        """Return the borrow limit for a given Role enum value."""
        from models import Role
        return {
            Role.USER:  self.MAX_BOOKS_USER,
            Role.STAFF: self.MAX_BOOKS_STAFF,
            Role.ADMIN: self.MAX_BOOKS_ADMIN,
        }.get(role, self.MAX_BOOKS_USER)


# ── Singleton instance ────────────────────────────────────────────────────────

config = Config()


# ── Persistence ───────────────────────────────────────────────────────────────

CONFIG_FILE = "library_config.json"


def save_config(filepath: str = CONFIG_FILE):
    """Save current config to JSON."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(asdict(config), f, indent=2)
    print(f"⚙️  Config saved to '{filepath}'")


def load_config(filepath: str = CONFIG_FILE):
    """Load config from JSON, overwriting the current singleton."""
    global config
    if not os.path.exists(filepath):
        print(f"⚙️  No config file found at '{filepath}'. Using defaults.")
        return
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    for key, val in data.items():
        if hasattr(config, key):
            setattr(config, key, val)
    print(f"⚙️  Config loaded from '{filepath}'")


def reset_config():
    """Reset all settings to defaults."""
    global config
    config = Config()
    print("⚙️  Config reset to defaults.")
