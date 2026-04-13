"""
validators.py - Input Validation for the Library Management System

All validators raise exceptions.ValidationError or exceptions.WeakPasswordError
on failure, and return the (possibly normalised) value on success.
"""

import re
from exceptions import ValidationError, WeakPasswordError
from config import config


# ── String helpers ────────────────────────────────────────────────────────────

def _require_non_empty(value: str, field: str) -> str:
    value = value.strip()
    if not value:
        raise ValidationError(field, "must not be empty")
    return value


# ── Username ──────────────────────────────────────────────────────────────────

USERNAME_RE = re.compile(r'^[a-zA-Z0-9_]{3,30}$')

def validate_username(username: str) -> str:
    """3–30 chars, letters/digits/underscores only."""
    username = _require_non_empty(username, "username")
    if not USERNAME_RE.match(username):
        raise ValidationError(
            "username",
            "must be 3–30 characters and contain only letters, digits, or underscores"
        )
    return username.lower()


# ── Password ──────────────────────────────────────────────────────────────────

def validate_password(password: str) -> str:
    """Enforce the password policy defined in config."""
    if len(password) < config.PASSWORD_MIN_LENGTH:
        raise WeakPasswordError(
            f"must be at least {config.PASSWORD_MIN_LENGTH} characters long"
        )
    if config.PASSWORD_REQUIRE_UPPER and not any(c.isupper() for c in password):
        raise WeakPasswordError("must contain at least one uppercase letter")
    if config.PASSWORD_REQUIRE_LOWER and not any(c.islower() for c in password):
        raise WeakPasswordError("must contain at least one lowercase letter")
    if config.PASSWORD_REQUIRE_DIGIT and not any(c.isdigit() for c in password):
        raise WeakPasswordError("must contain at least one digit")
    if config.PASSWORD_REQUIRE_SPECIAL:
        if not any(c in config.PASSWORD_SPECIAL_CHARS for c in password):
            raise WeakPasswordError(
                f"must contain at least one special character ({config.PASSWORD_SPECIAL_CHARS})"
            )
    return password


def password_strength(password: str) -> dict:
    """
    Score a password 0–5 and return a breakdown dict.
    Does NOT raise; useful for UI feedback.
    """
    score = 0
    checks = {
        "length_ok":   len(password) >= config.PASSWORD_MIN_LENGTH,
        "has_upper":   any(c.isupper() for c in password),
        "has_lower":   any(c.islower() for c in password),
        "has_digit":   any(c.isdigit() for c in password),
        "has_special": any(c in config.PASSWORD_SPECIAL_CHARS for c in password),
    }
    score = sum(checks.values())
    labels = {0: "Very Weak", 1: "Weak", 2: "Fair", 3: "Good", 4: "Strong", 5: "Very Strong"}
    return {"score": score, "label": labels[score], **checks}


# ── Email ─────────────────────────────────────────────────────────────────────

EMAIL_RE = re.compile(r'^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$')

def validate_email(email: str) -> str:
    email = _require_non_empty(email, "email").lower()
    if not EMAIL_RE.match(email):
        raise ValidationError("email", "must be a valid email address (e.g. user@example.com)")
    return email


# ── Phone ─────────────────────────────────────────────────────────────────────

PHONE_RE = re.compile(r'^\+?[0-9 \-()]{7,15}$')

def validate_phone(phone: str) -> str:
    """Optional field — empty string passes silently."""
    if not phone.strip():
        return ""
    digits = re.sub(r'\D', '', phone)
    if len(digits) < 7 or len(digits) > 15:
        raise ValidationError("phone", "must contain 7–15 digits")
    return phone.strip()


# ── Full Name ─────────────────────────────────────────────────────────────────

def validate_full_name(name: str) -> str:
    name = _require_non_empty(name, "full_name")
    if len(name) > 100:
        raise ValidationError("full_name", "must be 100 characters or fewer")
    if any(c.isdigit() for c in name):
        raise ValidationError("full_name", "must not contain digits")
    return name.strip()


# ── ISBN ──────────────────────────────────────────────────────────────────────

ISBN10_RE = re.compile(r'^(?:\d[\ |-]?){9}[\d|X]$')
ISBN13_RE = re.compile(r'^(?:\d[\ |-]?){13}$')

def validate_isbn(isbn: str) -> str:
    isbn = _require_non_empty(isbn, "isbn")
    clean = isbn.replace("-", "").replace(" ", "")
    if not (ISBN10_RE.match(clean) or ISBN13_RE.match(clean) or clean.isdigit()):
        raise ValidationError(
            "isbn", "must be a valid ISBN-10 or ISBN-13 (digits and optional dashes)"
        )
    return isbn.strip()


# ── Book fields ───────────────────────────────────────────────────────────────

def validate_title(title: str) -> str:
    title = _require_non_empty(title, "title")
    if len(title) > 200:
        raise ValidationError("title", "must be 200 characters or fewer")
    return title.strip()


def validate_author(author: str) -> str:
    author = _require_non_empty(author, "author")
    if len(author) > 150:
        raise ValidationError("author", "must be 150 characters or fewer")
    return author.strip()


def validate_year(year) -> int:
    try:
        year = int(year)
    except (TypeError, ValueError):
        raise ValidationError("year", "must be a four-digit integer")
    if year < 1000 or year > 2100:
        raise ValidationError("year", "must be between 1000 and 2100")
    return year


def validate_copies(copies) -> int:
    try:
        copies = int(copies)
    except (TypeError, ValueError):
        raise ValidationError("copies", "must be a positive integer")
    if copies <= 0:
        raise ValidationError("copies", "must be at least 1")
    if copies > 10_000:
        raise ValidationError("copies", "unrealistically large (max 10,000)")
    return copies


def validate_genre(genre: str) -> str:
    genre = _require_non_empty(genre, "genre")
    if len(genre) > 50:
        raise ValidationError("genre", "must be 50 characters or fewer")
    return genre.strip()


# ── Fine amount ───────────────────────────────────────────────────────────────

def validate_fine_amount(amount, outstanding: float) -> float:
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        raise ValidationError("amount", "must be a numeric value")
    if amount <= 0:
        raise ValidationError("amount", "must be greater than zero")
    if amount > outstanding:
        raise ValidationError(
            "amount", f"cannot exceed outstanding fine of ₹{outstanding:.2f}"
        )
    return round(amount, 2)


# ── Convenience: validate a full user registration dict ───────────────────────

def validate_registration(username: str, password: str,
                           full_name: str, email: str, phone: str = "") -> dict:
    """
    Validate all fields for a new user registration.
    Returns a dict of normalised values, or raises on the first failure.
    """
    return {
        "username":  validate_username(username),
        "password":  validate_password(password),
        "full_name": validate_full_name(full_name),
        "email":     validate_email(email),
        "phone":     validate_phone(phone),
    }


def validate_book_fields(isbn: str, title: str, author: str,
                          year, copies, genre: str) -> dict:
    """
    Validate all required fields for adding a book.
    Returns a dict of normalised values, or raises on the first failure.
    """
    return {
        "isbn":   validate_isbn(isbn),
        "title":  validate_title(title),
        "author": validate_author(author),
        "year":   validate_year(year),
        "copies": validate_copies(copies),
        "genre":  validate_genre(genre),
    }
