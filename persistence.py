"""
persistence.py - JSON-based persistent storage for the Library Management System

Usage:
    from persistence import save_library, load_library

    save_library(lib, "library_data.json")
    lib = load_library("library_data.json")
"""

import json
import os
from datetime import datetime, date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from library import LibrarySystem

from models import User, Book, BorrowRecord, Reservation, Role, BookStatus


# ── Serialisers ───────────────────────────────────────────────────────────────

def _ser_user(u: User) -> dict:
    return {
        "user_id": u.user_id,
        "username": u.username,
        "password_hash": u.password_hash,
        "role": u.role.value,
        "full_name": u.full_name,
        "email": u.email,
        "phone": u.phone,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat(),
        "borrowed_books": u.borrowed_books,
        "fine_amount": u.fine_amount,
    }


def _ser_book(b: Book) -> dict:
    return {
        "book_id": b.book_id,
        "isbn": b.isbn,
        "title": b.title,
        "author": b.author,
        "publisher": b.publisher,
        "year": b.year,
        "genre": b.genre,
        "total_copies": b.total_copies,
        "available_copies": b.available_copies,
        "status": b.status.value,
        "description": b.description,
        "location": b.location,
        "added_at": b.added_at.isoformat(),
    }


def _ser_record(r: BorrowRecord) -> dict:
    return {
        "record_id": r.record_id,
        "user_id": r.user_id,
        "book_id": r.book_id,
        "borrow_date": r.borrow_date.isoformat(),
        "due_date": r.due_date.isoformat(),
        "return_date": r.return_date.isoformat() if r.return_date else None,
        "fine": r.fine,
        "is_returned": r.is_returned,
        "notes": r.notes,
    }


def _ser_reservation(r: Reservation) -> dict:
    return {
        "reservation_id": r.reservation_id,
        "user_id": r.user_id,
        "book_id": r.book_id,
        "reserved_at": r.reserved_at.isoformat(),
        "expires_at": r.expires_at.isoformat() if r.expires_at else None,
        "is_active": r.is_active,
    }


# ── Deserialisers ─────────────────────────────────────────────────────────────

def _deser_user(d: dict) -> User:
    return User(
        user_id=d["user_id"],
        username=d["username"],
        password_hash=d["password_hash"],
        role=Role(d["role"]),
        full_name=d["full_name"],
        email=d["email"],
        phone=d.get("phone", ""),
        is_active=d.get("is_active", True),
        created_at=datetime.fromisoformat(d["created_at"]),
        borrowed_books=d.get("borrowed_books", []),
        fine_amount=d.get("fine_amount", 0.0),
    )


def _deser_book(d: dict) -> Book:
    return Book(
        book_id=d["book_id"],
        isbn=d["isbn"],
        title=d["title"],
        author=d["author"],
        publisher=d["publisher"],
        year=d["year"],
        genre=d["genre"],
        total_copies=d["total_copies"],
        available_copies=d["available_copies"],
        status=BookStatus(d.get("status", "available")),
        description=d.get("description", ""),
        location=d.get("location", ""),
        added_at=datetime.fromisoformat(d["added_at"]),
    )


def _deser_record(d: dict) -> BorrowRecord:
    return BorrowRecord(
        record_id=d["record_id"],
        user_id=d["user_id"],
        book_id=d["book_id"],
        borrow_date=date.fromisoformat(d["borrow_date"]),
        due_date=date.fromisoformat(d["due_date"]),
        return_date=date.fromisoformat(d["return_date"]) if d.get("return_date") else None,
        fine=d.get("fine", 0.0),
        is_returned=d.get("is_returned", False),
        notes=d.get("notes", ""),
    )


def _deser_reservation(d: dict) -> Reservation:
    return Reservation(
        reservation_id=d["reservation_id"],
        user_id=d["user_id"],
        book_id=d["book_id"],
        reserved_at=datetime.fromisoformat(d["reserved_at"]),
        expires_at=datetime.fromisoformat(d["expires_at"]) if d.get("expires_at") else None,
        is_active=d.get("is_active", True),
    )


# ── Public API ────────────────────────────────────────────────────────────────

def save_library(lib: "LibrarySystem", filepath: str = "library_data.json"):
    """Serialise the entire library state to a JSON file."""
    data = {
        "library_name": lib.library_name,
        "saved_at": datetime.now().isoformat(),
        "users": [_ser_user(u) for u in lib._users.values()],
        "books": [_ser_book(b) for b in lib._books.values()],
        "borrow_records": [_ser_record(r) for r in lib._borrow_records.values()],
        "reservations": [_ser_reservation(r) for r in lib._reservations.values()],
        "pending_registrations": list(lib._pending_registrations.values()),
        "logs": lib._logs,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    size_kb = os.path.getsize(filepath) / 1024
    print(f"💾 Library saved to '{filepath}' ({size_kb:.1f} KB)")


def load_library(filepath: str = "library_data.json") -> "LibrarySystem":
    """Restore library state from a JSON file. Returns a fully populated LibrarySystem."""
    from library import LibrarySystem   # local import to avoid circular

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"No save file found at '{filepath}'")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Build a blank system (this creates the default admin too)
    lib = LibrarySystem(data.get("library_name", "Library"))

    # Overwrite with saved state
    lib._users = {u["user_id"]: _deser_user(u) for u in data.get("users", [])}
    lib._books = {b["book_id"]: _deser_book(b) for b in data.get("books", [])}
    lib._borrow_records = {r["record_id"]: _deser_record(r)
                           for r in data.get("borrow_records", [])}
    lib._reservations = {r["reservation_id"]: _deser_reservation(r)
                         for r in data.get("reservations", [])}
    lib._pending_registrations = {r["reg_id"]: r
                                  for r in data.get("pending_registrations", [])}
    lib._logs = data.get("logs", [])

    saved_at = data.get("saved_at", "unknown")[:19]
    print(f"📂 Library loaded from '{filepath}' (saved {saved_at})")
    print(f"   {len(lib._users)} users | {len(lib._books)} books | "
          f"{len(lib._borrow_records)} records")
    return lib
