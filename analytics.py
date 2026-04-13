"""
analytics.py - Advanced Reporting & Analytics Dashboard

Available reports (all require ADMIN or STAFF unless noted):
  - overdue_report()         : list all overdue borrows with accrued fines
  - due_soon_report()        : borrows due within N days (reminder candidates)
  - top_borrowed_books()     : most borrowed titles
  - top_borrowers()          : most active users
  - genre_distribution()     : genre breakdown across inventory
  - fine_summary()           : outstanding fines by user
  - monthly_activity()       : borrow/return counts grouped by month
  - full_dashboard()         : all of the above in one call
"""

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from library import LibrarySystem
    from models import User


FINE_PER_DAY = 5.0   # keep in sync with library.py


def _div(title: str, width: int = 70):
    print(f"\n{'─'*width}")
    print(f"  {title}")
    print(f"{'─'*width}")


def overdue_report(lib: "LibrarySystem") -> list:
    """Return list of (record, user, book, days_overdue, accrued_fine) for active overdue borrows."""
    today = date.today()
    results = []
    for r in lib._borrow_records.values():
        if not r.is_returned and r.due_date < today:
            days = (today - r.due_date).days
            fine = days * FINE_PER_DAY
            user = lib._users.get(r.user_id)
            book = lib._books.get(r.book_id)
            results.append((r, user, book, days, fine))
    results.sort(key=lambda x: x[3], reverse=True)   # most overdue first
    return results


def print_overdue_report(lib: "LibrarySystem"):
    rows = overdue_report(lib)
    _div("📛 OVERDUE BOOKS REPORT")
    if not rows:
        print("  ✅ No overdue books!")
        return
    print(f"  {'Record':<14} {'User':<18} {'Book':<28} {'Due Date':<12} {'Days':<6} {'Fine'}")
    print(f"  {'─'*85}")
    for r, user, book, days, fine in rows:
        uname = user.username if user else r.user_id
        btitle = (book.title[:26] if book else r.book_id)
        print(f"  {r.record_id:<14} {uname:<18} {btitle:<28} {str(r.due_date):<12} {days:<6} ₹{fine:.2f}")
    total_fine = sum(x[4] for x in rows)
    print(f"\n  Total overdue: {len(rows)} book(s)   Accrued fines: ₹{total_fine:.2f}")


def print_due_soon_report(lib: "LibrarySystem", within_days: int = 3):
    today = date.today()
    cutoff = today + timedelta(days=within_days)
    rows = [
        (r, lib._users.get(r.user_id), lib._books.get(r.book_id))
        for r in lib._borrow_records.values()
        if not r.is_returned and today <= r.due_date <= cutoff
    ]
    rows.sort(key=lambda x: x[0].due_date)
    _div(f"⏰ BOOKS DUE WITHIN {within_days} DAY(S)")
    if not rows:
        print(f"  No books due within the next {within_days} day(s).")
        return
    print(f"  {'Record':<14} {'User':<18} {'Book':<30} {'Due Date':<12} {'Days Left'}")
    print(f"  {'─'*80}")
    for r, user, book in rows:
        uname = user.username if user else r.user_id
        btitle = book.title[:28] if book else r.book_id
        days_left = (r.due_date - today).days
        print(f"  {r.record_id:<14} {uname:<18} {btitle:<30} {str(r.due_date):<12} {days_left}")
    print(f"\n  Total: {len(rows)} borrow(s) due soon")


def print_top_borrowed_books(lib: "LibrarySystem", top_n: int = 10):
    freq: Counter = Counter()
    for r in lib._borrow_records.values():
        freq[r.book_id] += 1

    _div(f"🏆 TOP {top_n} MOST BORROWED BOOKS")
    if not freq:
        print("  No borrow history yet.")
        return
    print(f"  {'Rank':<6} {'Title':<35} {'Author':<22} {'Borrows'}")
    print(f"  {'─'*70}")
    for rank, (book_id, count) in enumerate(freq.most_common(top_n), 1):
        book = lib._books.get(book_id)
        title = book.title[:33] if book else book_id
        author = book.author[:20] if book else "—"
        print(f"  {rank:<6} {title:<35} {author:<22} {count}")


def print_top_borrowers(lib: "LibrarySystem", top_n: int = 10):
    freq: Counter = Counter()
    for r in lib._borrow_records.values():
        freq[r.user_id] += 1

    _div(f"📚 TOP {top_n} MOST ACTIVE BORROWERS")
    if not freq:
        print("  No borrow history yet.")
        return
    print(f"  {'Rank':<6} {'Username':<18} {'Full Name':<25} {'Borrows':<10} {'Active Fine'}")
    print(f"  {'─'*70}")
    for rank, (user_id, count) in enumerate(freq.most_common(top_n), 1):
        user = lib._users.get(user_id)
        uname = user.username if user else user_id
        fname = user.full_name[:23] if user else "—"
        fine = f"₹{user.fine_amount:.2f}" if user else "—"
        print(f"  {rank:<6} {uname:<18} {fname:<25} {count:<10} {fine}")


def print_genre_distribution(lib: "LibrarySystem"):
    genre_titles: Counter = Counter()
    genre_copies: Counter = Counter()
    genre_borrows: Counter = Counter()

    for b in lib._books.values():
        genre_titles[b.genre] += 1
        genre_copies[b.genre] += b.total_copies

    book_genre = {b.book_id: b.genre for b in lib._books.values()}
    for r in lib._borrow_records.values():
        g = book_genre.get(r.book_id, "Unknown")
        genre_borrows[g] += 1

    _div("📊 GENRE DISTRIBUTION")
    all_genres = set(genre_titles) | set(genre_borrows)
    if not all_genres:
        print("  No books in the system.")
        return
    print(f"  {'Genre':<22} {'Titles':<8} {'Copies':<8} {'Borrows':<10} {'Pop. Index'}")
    print(f"  {'─'*60}")
    rows = sorted(all_genres, key=lambda g: genre_borrows[g], reverse=True)
    for g in rows:
        copies = genre_copies[g]
        borrows = genre_borrows[g]
        pop = f"{borrows/copies*100:.0f}%" if copies else "—"
        print(f"  {g:<22} {genre_titles[g]:<8} {copies:<8} {borrows:<10} {pop}")


def print_fine_summary(lib: "LibrarySystem"):
    users_with_fines = [(u, u.fine_amount) for u in lib._users.values() if u.fine_amount > 0]
    users_with_fines.sort(key=lambda x: x[1], reverse=True)

    _div("💰 OUTSTANDING FINES SUMMARY")
    if not users_with_fines:
        print("  ✅ No outstanding fines.")
        return
    print(f"  {'Username':<18} {'Full Name':<25} {'Fine Amount'}")
    print(f"  {'─'*55}")
    for user, fine in users_with_fines:
        print(f"  {user.username:<18} {user.full_name:<25} ₹{fine:.2f}")
    total = sum(f for _, f in users_with_fines)
    print(f"\n  Total outstanding: ₹{total:.2f} across {len(users_with_fines)} user(s)")


def print_monthly_activity(lib: "LibrarySystem"):
    borrows_by_month: Counter = Counter()
    returns_by_month: Counter = Counter()

    for r in lib._borrow_records.values():
        key = r.borrow_date.strftime("%Y-%m")
        borrows_by_month[key] += 1
        if r.return_date:
            key2 = r.return_date.strftime("%Y-%m")
            returns_by_month[key2] += 1

    _div("📅 MONTHLY ACTIVITY")
    all_months = sorted(set(borrows_by_month) | set(returns_by_month))
    if not all_months:
        print("  No activity yet.")
        return
    print(f"  {'Month':<12} {'Borrows':<10} {'Returns':<10} {'Net'}")
    print(f"  {'─'*40}")
    for month in all_months:
        b = borrows_by_month[month]
        r = returns_by_month[month]
        net = b - r
        net_str = f"+{net}" if net >= 0 else str(net)
        print(f"  {month:<12} {b:<10} {r:<10} {net_str}")


def print_inventory_health(lib: "LibrarySystem"):
    total_titles = len(lib._books)
    total_copies = sum(b.total_copies for b in lib._books.values())
    available = sum(b.available_copies for b in lib._books.values())
    borrowed = total_copies - available
    utilisation = borrowed / total_copies * 100 if total_copies else 0

    overdue_count = len(overdue_report(lib))

    _div("🏥 INVENTORY HEALTH")
    print(f"  Total Titles      : {total_titles}")
    print(f"  Total Copies      : {total_copies}")
    print(f"  Currently Borrowed: {borrowed}  ({utilisation:.1f}% utilisation)")
    print(f"  Available         : {available}")
    print(f"  Overdue           : {overdue_count}")
    bar_len = 30
    filled = int(utilisation / 100 * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"\n  Utilisation  [{bar}] {utilisation:.1f}%")


def full_dashboard(lib: "LibrarySystem"):
    print(f"\n{'═'*70}")
    print(f"  📊  LIBRARY ANALYTICS DASHBOARD — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  {lib.library_name}")
    print(f"{'═'*70}")

    print_inventory_health(lib)
    print_overdue_report(lib)
    print_due_soon_report(lib, within_days=3)
    print_top_borrowed_books(lib, top_n=5)
    print_top_borrowers(lib, top_n=5)
    print_genre_distribution(lib)
    print_fine_summary(lib)
    print_monthly_activity(lib)

    print(f"\n{'═'*70}")
    print(f"  End of Dashboard Report")
    print(f"{'═'*70}\n")
