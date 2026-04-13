"""
reports_export.py - Export Library Reports to CSV and Text Files

Available exports:
    export_books_csv()           - full book catalogue
    export_users_csv()           - all users (passwords excluded)
    export_borrow_records_csv()  - complete borrow history
    export_overdue_csv()         - currently overdue borrows
    export_fines_csv()           - outstanding fines per user
    export_inventory_txt()       - human-readable inventory report
    export_all()                 - run all exports into a timestamped folder

All functions require the caller to have 'generate_reports' permission.
"""

import csv
import os
from datetime import datetime, date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from library import LibrarySystem
    from models import User

from config import config
from exceptions import ExportError


def _ensure_dir(directory: str) -> str:
    os.makedirs(directory, exist_ok=True)
    return directory


def _filepath(directory: str, filename: str) -> str:
    return os.path.join(directory, filename)


def _check_permission(actor: "User", action: str = "generate_reports"):
    from auth import has_permission
    from exceptions import PermissionDeniedError
    if not has_permission(actor, action):
        raise PermissionDeniedError(actor.role.value, action)


# ── Individual exports ────────────────────────────────────────────────────────

def export_books_csv(lib: "LibrarySystem", actor: "User",
                     directory: str = None) -> str:
    """Export full book catalogue to CSV."""
    _check_permission(actor, "view_reports")
    directory = directory or config.REPORTS_DIR
    _ensure_dir(directory)
    fp = _filepath(directory, "books.csv")

    with open(fp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["book_id","isbn","title","author","publisher","year",
                    "genre","total_copies","available_copies","status","location","added_at"])
        for b in lib._books.values():
            w.writerow([b.book_id, b.isbn, b.title, b.author, b.publisher,
                        b.year, b.genre, b.total_copies, b.available_copies,
                        b.status.value, b.location,
                        b.added_at.strftime(config.EXPORT_DATE_FORMAT)])
    print(f"📤 Books exported → '{fp}' ({len(lib._books)} rows)")
    return fp


def export_users_csv(lib: "LibrarySystem", actor: "User",
                     directory: str = None) -> str:
    """Export user list to CSV (passwords omitted)."""
    _check_permission(actor)
    directory = directory or config.REPORTS_DIR
    _ensure_dir(directory)
    fp = _filepath(directory, "users.csv")

    with open(fp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["user_id","username","role","full_name","email",
                    "phone","is_active","fine_amount","active_borrows","created_at"])
        for u in lib._users.values():
            borrows = len(u.borrowed_books)
            w.writerow([u.user_id, u.username, u.role.value, u.full_name,
                        u.email, u.phone, u.is_active, f"{u.fine_amount:.2f}",
                        borrows, u.created_at.strftime(config.EXPORT_DATE_FORMAT)])
    print(f"📤 Users exported → '{fp}' ({len(lib._users)} rows)")
    return fp


def export_borrow_records_csv(lib: "LibrarySystem", actor: "User",
                               directory: str = None,
                               active_only: bool = False) -> str:
    """Export full borrow history to CSV."""
    _check_permission(actor, "view_borrow_history")
    directory = directory or config.REPORTS_DIR
    _ensure_dir(directory)
    suffix = "_active" if active_only else ""
    fp = _filepath(directory, f"borrow_records{suffix}.csv")

    records = list(lib._borrow_records.values())
    if active_only:
        records = [r for r in records if not r.is_returned]

    with open(fp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["record_id","user_id","username","book_id","book_title",
                    "borrow_date","due_date","return_date","fine","is_returned","notes"])
        for r in records:
            user = lib._users.get(r.user_id)
            book = lib._books.get(r.book_id)
            w.writerow([
                r.record_id,
                r.user_id,
                user.username if user else "—",
                r.book_id,
                book.title if book else "—",
                str(r.borrow_date),
                str(r.due_date),
                str(r.return_date) if r.return_date else "",
                f"{r.fine:.2f}",
                r.is_returned,
                r.notes,
            ])
    print(f"📤 Borrow records exported → '{fp}' ({len(records)} rows)")
    return fp


def export_overdue_csv(lib: "LibrarySystem", actor: "User",
                        directory: str = None) -> str:
    """Export currently overdue borrows to CSV."""
    _check_permission(actor, "view_reports")
    from analytics import overdue_report
    directory = directory or config.REPORTS_DIR
    _ensure_dir(directory)
    fp = _filepath(directory, "overdue.csv")
    rows = overdue_report(lib)

    with open(fp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["record_id","user_id","username","book_id","book_title",
                    "borrow_date","due_date","days_overdue","accrued_fine"])
        for r, user, book, days, fine in rows:
            w.writerow([
                r.record_id,
                r.user_id,
                user.username if user else "—",
                r.book_id,
                book.title if book else "—",
                str(r.borrow_date),
                str(r.due_date),
                days,
                f"{fine:.2f}",
            ])
    print(f"📤 Overdue report exported → '{fp}' ({len(rows)} rows)")
    return fp


def export_fines_csv(lib: "LibrarySystem", actor: "User",
                      directory: str = None) -> str:
    """Export outstanding fines per user to CSV."""
    _check_permission(actor, "view_reports")
    directory = directory or config.REPORTS_DIR
    _ensure_dir(directory)
    fp = _filepath(directory, "fines.csv")
    users_with_fines = [(u, u.fine_amount) for u in lib._users.values() if u.fine_amount > 0]

    with open(fp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["user_id","username","full_name","email","phone","outstanding_fine"])
        for u, fine in sorted(users_with_fines, key=lambda x: -x[1]):
            w.writerow([u.user_id, u.username, u.full_name, u.email, u.phone, f"{fine:.2f}"])
    print(f"📤 Fines report exported → '{fp}' ({len(users_with_fines)} rows)")
    return fp


def export_inventory_txt(lib: "LibrarySystem", actor: "User",
                          directory: str = None) -> str:
    """Export a human-readable inventory report to a text file."""
    _check_permission(actor, "view_reports")
    directory = directory or config.REPORTS_DIR
    _ensure_dir(directory)
    fp = _filepath(directory, "inventory.txt")

    total_copies = sum(b.total_copies for b in lib._books.values())
    available = sum(b.available_copies for b in lib._books.values())

    with open(fp, "w", encoding="utf-8") as f:
        f.write(f"INVENTORY REPORT — {lib.library_name}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 90 + "\n\n")
        f.write(f"Total titles  : {len(lib._books)}\n")
        f.write(f"Total copies  : {total_copies}\n")
        f.write(f"Available     : {available}\n")
        f.write(f"Borrowed      : {total_copies - available}\n\n")
        f.write("-" * 90 + "\n")
        f.write(f"{'ID':<14} {'Title':<35} {'Author':<22} {'Genre':<18} {'Avail/Total':<12} Location\n")
        f.write("-" * 90 + "\n")
        for b in sorted(lib._books.values(), key=lambda x: x.title):
            avail = f"{b.available_copies}/{b.total_copies}"
            f.write(f"{b.book_id:<14} {b.title[:33]:<35} {b.author[:20]:<22} "
                    f"{b.genre[:16]:<18} {avail:<12} {b.location}\n")
        f.write("-" * 90 + "\n")

    print(f"📤 Inventory report exported → '{fp}'")
    return fp


def export_all(lib: "LibrarySystem", actor: "User",
               base_dir: str = None) -> str:
    """Run all exports into a timestamped subdirectory."""
    _check_permission(actor)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    directory = os.path.join(base_dir or config.REPORTS_DIR, f"export_{ts}")
    _ensure_dir(directory)

    print(f"\n📦 Exporting all reports to '{directory}' …")
    export_books_csv(lib, actor, directory)
    export_users_csv(lib, actor, directory)
    export_borrow_records_csv(lib, actor, directory)
    export_overdue_csv(lib, actor, directory)
    export_fines_csv(lib, actor, directory)
    export_inventory_txt(lib, actor, directory)

    lib._log(actor.username, "EXPORT_ALL", f"Exported all reports to '{directory}'")
    print(f"✅ All reports saved to '{directory}'\n")
    return directory
