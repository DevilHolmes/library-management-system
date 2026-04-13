"""
audit.py - Structured Audit Trail

Provides richer audit capabilities on top of the basic _logs list:
  - Typed AuditEntry dataclass
  - Filter by actor, action category, date range
  - Export to CSV or plain-text
  - Summary statistics
  - Integration helper: attach to a LibrarySystem instance
"""

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from library import LibrarySystem


# ── Entry categories (for grouping / filtering) ───────────────────────────────

CATEGORY_MAP = {
    "LOGIN":           "auth",
    "LOGIN_FAIL":      "auth",
    "REGISTER_REQUEST":"registration",
    "APPROVE_REG":     "registration",
    "REJECT_REG":      "registration",
    "CREATE_USER":     "user_mgmt",
    "DELETE_USER":     "user_mgmt",
    "TOGGLE_USER":     "user_mgmt",
    "ADD_BOOK":        "inventory",
    "ADD_COPIES":      "inventory",
    "DELETE_BOOK":     "inventory",
    "UPDATE_BOOK":     "inventory",
    "BORROW":          "circulation",
    "RETURN":          "circulation",
    "RESERVE":         "circulation",
    "WAIVE_FINE":      "finance",
    "COLLECT_FINE":    "finance",
    "OVERDUE_ALERTS":  "alerts",
    "DUE_REMINDERS":   "alerts",
}


@dataclass
class AuditEntry:
    timestamp: datetime
    actor: str
    action: str
    detail: str
    category: str = ""

    def __post_init__(self):
        if not self.category:
            self.category = CATEGORY_MAP.get(self.action, "system")

    @classmethod
    def from_dict(cls, d: dict) -> "AuditEntry":
        return cls(
            timestamp=datetime.fromisoformat(d["timestamp"]),
            actor=d["actor"],
            action=d["action"],
            detail=d["detail"],
        )

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor,
            "action": self.action,
            "detail": self.detail,
            "category": self.category,
        }


class AuditTrail:
    """
    Wraps a LibrarySystem's raw _logs list and provides structured access.
    Attach once after creating/loading the lib:
        audit = AuditTrail(lib)
    """

    def __init__(self, lib: "LibrarySystem"):
        self._lib = lib

    def _entries(self) -> List[AuditEntry]:
        return [AuditEntry.from_dict(d) for d in self._lib._logs]

    # ── Filtering ─────────────────────────────────────────────────────────────

    def filter(
        self,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        category: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        search: Optional[str] = None,
    ) -> List[AuditEntry]:
        """
        Return filtered audit entries. All parameters are optional AND-combined.

        Args:
            actor    : exact username match (case-insensitive)
            action   : exact action code match (e.g. "BORROW")
            category : category string (e.g. "circulation", "finance")
            from_date: include entries on or after this date
            to_date  : include entries on or before this date
            search   : substring search across actor + action + detail
        """
        entries = self._entries()
        if actor:
            entries = [e for e in entries if e.actor.lower() == actor.lower()]
        if action:
            entries = [e for e in entries if e.action.upper() == action.upper()]
        if category:
            entries = [e for e in entries if e.category == category]
        if from_date:
            entries = [e for e in entries if e.timestamp.date() >= from_date]
        if to_date:
            entries = [e for e in entries if e.timestamp.date() <= to_date]
        if search:
            q = search.lower()
            entries = [e for e in entries
                       if q in e.actor.lower() or q in e.action.lower() or q in e.detail.lower()]
        return entries

    # ── Display ───────────────────────────────────────────────────────────────

    def print_entries(self, entries: Optional[List[AuditEntry]] = None,
                      title: str = "AUDIT LOG", last_n: int = 0):
        entries = entries if entries is not None else self._entries()
        if last_n:
            entries = entries[-last_n:]
        print(f"\n{'─'*90}")
        print(f"  🗒️  {title} ({len(entries)} entries)")
        print(f"{'─'*90}")
        print(f"  {'Timestamp':<20} {'Actor':<14} {'Category':<14} {'Action':<18} Detail")
        print(f"  {'─'*86}")
        for e in entries:
            ts = e.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            detail = e.detail[:40] + ("…" if len(e.detail) > 40 else "")
            print(f"  {ts:<20} {e.actor:<14} {e.category:<14} {e.action:<18} {detail}")
        print(f"{'─'*90}\n")

    # ── Statistics ────────────────────────────────────────────────────────────

    def summary(self):
        entries = self._entries()
        from collections import Counter
        cat_counts = Counter(e.category for e in entries)
        action_counts = Counter(e.action for e in entries)
        actor_counts = Counter(e.actor for e in entries)

        print(f"\n{'─'*60}")
        print("  📊 AUDIT SUMMARY")
        print(f"{'─'*60}")
        print(f"  Total entries : {len(entries)}")
        if entries:
            print(f"  From          : {entries[0].timestamp.strftime('%Y-%m-%d %H:%M')}")
            print(f"  To            : {entries[-1].timestamp.strftime('%Y-%m-%d %H:%M')}")
        print(f"\n  By Category:")
        for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
            print(f"    {cat:<20}: {cnt}")
        print(f"\n  Top 5 Actions:")
        for action, cnt in action_counts.most_common(5):
            print(f"    {action:<20}: {cnt}")
        print(f"\n  Top 5 Actors:")
        for actor, cnt in actor_counts.most_common(5):
            print(f"    {actor:<20}: {cnt}")
        print(f"{'─'*60}\n")

    # ── Export ────────────────────────────────────────────────────────────────

    def export_csv(self, filepath: str,
                   entries: Optional[List[AuditEntry]] = None):
        """Export audit entries to a CSV file."""
        entries = entries if entries is not None else self._entries()
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["timestamp", "actor", "category", "action", "detail"])
            writer.writeheader()
            for e in entries:
                writer.writerow(e.to_dict())
        print(f"📤 Audit log exported to '{filepath}' ({len(entries)} rows)")

    def export_txt(self, filepath: str,
                   entries: Optional[List[AuditEntry]] = None):
        """Export audit entries to a plain-text file."""
        entries = entries if entries is not None else self._entries()
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"AUDIT LOG — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write("=" * 90 + "\n")
            for e in entries:
                ts = e.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{ts}] {e.actor:<14} | {e.category:<13} | {e.action:<17} | {e.detail}\n")
        print(f"📤 Audit log exported to '{filepath}' ({len(entries)} lines)")
