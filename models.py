"""
models.py - Core Data Models for the Library Management System

Defines:
  - Role          : user role enum (admin / staff / user)
  - BookStatus    : availability enum (available / borrowed / reserved / removed)
  - User          : library member / staff / admin
  - Book          : catalogue entry
  - BorrowRecord  : single borrow transaction
  - Reservation   : book hold request
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import List, Optional


# ── Enumerations ──────────────────────────────────────────────────────────────

class Role(Enum):
    ADMIN = "admin"
    STAFF = "staff"
    USER  = "user"


class BookStatus(Enum):
    AVAILABLE = "available"
    BORROWED  = "borrowed"
    RESERVED  = "reserved"
    REMOVED   = "removed"


# ── User ──────────────────────────────────────────────────────────────────────

@dataclass
class User:
    user_id:       str
    username:      str
    password_hash: str
    role:          Role
    full_name:     str
    email:         str
    phone:         str = ""
    is_active:     bool = True
    created_at:    datetime = field(default_factory=datetime.now)
    borrowed_books: List[str] = field(default_factory=list)   # list of book_ids
    fine_amount:   float = 0.0

    def __repr__(self):
        return (f"<User {self.user_id} username={self.username!r} "
                f"role={self.role.value} active={self.is_active}>")


# ── Book ──────────────────────────────────────────────────────────────────────

@dataclass
class Book:
    book_id:          str
    isbn:             str
    title:            str
    author:           str
    publisher:        str
    year:             int
    genre:            str
    total_copies:     int
    available_copies: int
    status:           BookStatus = BookStatus.AVAILABLE
    description:      str = ""
    location:         str = ""
    added_at:         datetime = field(default_factory=datetime.now)

    def __repr__(self):
        return (f"<Book {self.book_id} title={self.title!r} "
                f"avail={self.available_copies}/{self.total_copies}>")


# ── BorrowRecord ──────────────────────────────────────────────────────────────

@dataclass
class BorrowRecord:
    record_id:   str
    user_id:     str
    book_id:     str
    borrow_date: date
    due_date:    date
    return_date: Optional[date] = None
    fine:        float = 0.0
    is_returned: bool = False
    notes:       str = ""

    def __repr__(self):
        return (f"<BorrowRecord {self.record_id} user={self.user_id} "
                f"book={self.book_id} returned={self.is_returned}>")


# ── Reservation ───────────────────────────────────────────────────────────────

@dataclass
class Reservation:
    reservation_id: str
    user_id:        str
    book_id:        str
    reserved_at:    datetime = field(default_factory=datetime.now)
    expires_at:     Optional[datetime] = None
    is_active:      bool = True

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def __repr__(self):
        return (f"<Reservation {self.reservation_id} user={self.user_id} "
                f"book={self.book_id} active={self.is_active}>")
