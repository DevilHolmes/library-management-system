"""
recommender.py - Book Recommendation Engine

Strategies (applied in priority order):
  1. Genre affinity  — books from genres the user borrows most
  2. Author affinity — other books by authors the user has read
  3. Popular picks   — most-borrowed books the user hasn't read yet
  4. New arrivals    — recently added books (fallback)
"""

from collections import Counter
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from library import LibrarySystem
    from models import User, Book


def recommend_books(lib: "LibrarySystem", user: "User",
                    top_n: int = 5) -> List["Book"]:
    """
    Return up to `top_n` available books recommended for `user`.
    Books the user currently holds or has returned are excluded.
    """
    from models import BookStatus   # avoid circular at module level

    # Books the user has ever interacted with (borrowed or currently holds)
    touched_ids = set(user.borrowed_books)
    for r in lib._borrow_records.values():
        if r.user_id == user.user_id:
            touched_ids.add(r.book_id)

    # Candidate pool: available books not yet touched
    candidates = [
        b for b in lib._books.values()
        if b.book_id not in touched_ids and b.available_copies > 0
    ]

    if not candidates:
        return []

    # ── Build preference profile from borrow history ───────────────────────
    genre_counts: Counter = Counter()
    author_counts: Counter = Counter()

    for r in lib._borrow_records.values():
        if r.user_id == user.user_id:
            book = lib._books.get(r.book_id)
            if book:
                genre_counts[book.genre] += 1
                author_counts[book.author] += 1

    # ── Score each candidate ───────────────────────────────────────────────
    # Borrow popularity across all users
    borrow_freq: Counter = Counter()
    for r in lib._borrow_records.values():
        borrow_freq[r.book_id] += 1

    def score(book: "Book") -> float:
        s = 0.0
        s += genre_counts.get(book.genre, 0) * 3.0   # genre match is strongest signal
        s += author_counts.get(book.author, 0) * 2.0  # author repeat
        s += borrow_freq.get(book.book_id, 0) * 0.5   # general popularity
        # Recency bonus: books added in the last 90 days get a small boost
        from datetime import datetime
        days_old = (datetime.now() - book.added_at).days
        if days_old <= 90:
            s += 1.0
        return s

    ranked = sorted(candidates, key=score, reverse=True)
    return ranked[:top_n]


def print_recommendations(lib: "LibrarySystem", user: "User", top_n: int = 5):
    recs = recommend_books(lib, user, top_n)

    print(f"\n{'═'*75}")
    print(f"  ✨ BOOK RECOMMENDATIONS FOR {user.full_name.upper()}")
    print(f"{'═'*75}")

    if not recs:
        print("  No recommendations available right now (you may have read everything! 🎉)")
        print(f"{'═'*75}\n")
        return

    for i, book in enumerate(recs, 1):
        avail = f"{book.available_copies}/{book.total_copies}"
        print(f"  {i}. {book.title}")
        print(f"     Author : {book.author}   Genre: {book.genre}   ({book.year})")
        print(f"     Copies : {avail} available   Shelf: {book.location or 'N/A'}")
        if book.description:
            desc = book.description[:90] + ("…" if len(book.description) > 90 else "")
            print(f"     About  : {desc}")
        print()

    print(f"{'═'*75}\n")
