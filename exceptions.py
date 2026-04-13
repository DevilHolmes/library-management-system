"""
exceptions.py - Custom Exception Hierarchy for the Library Management System

All library-specific exceptions inherit from LibraryError, making it easy
to catch any library error with a single except clause.
"""


class LibraryError(Exception):
    """Base class for all library management exceptions."""
    def __init__(self, message: str, code: str = "LIB_ERR"):
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self):
        return f"[{self.code}] {self.message}"


# ── Authentication & Access ───────────────────────────────────────────────────

class AuthenticationError(LibraryError):
    """Raised when login credentials are invalid."""
    def __init__(self, message="Invalid username or password."):
        super().__init__(message, "AUTH_001")


class AccountDeactivatedError(LibraryError):
    """Raised when a deactivated account attempts to log in."""
    def __init__(self, username: str):
        super().__init__(f"Account '{username}' is deactivated. Contact admin.", "AUTH_002")


class PermissionDeniedError(LibraryError):
    """Raised when a user lacks permission for an action."""
    def __init__(self, role: str, action: str):
        super().__init__(
            f"Role '{role}' does not have permission to perform '{action}'.", "AUTH_003")


class SessionExpiredError(LibraryError):
    """Raised when an expired session token is used."""
    def __init__(self):
        super().__init__("Session has expired. Please log in again.", "AUTH_004")


# ── User Management ───────────────────────────────────────────────────────────

class UserNotFoundError(LibraryError):
    """Raised when a user_id or username is not found."""
    def __init__(self, identifier: str):
        super().__init__(f"User '{identifier}' not found.", "USR_001")


class UserAlreadyExistsError(LibraryError):
    """Raised when trying to create a duplicate username."""
    def __init__(self, username: str):
        super().__init__(f"Username '{username}' is already taken.", "USR_002")


class RegistrationPendingError(LibraryError):
    """Raised when a duplicate self-registration is submitted."""
    def __init__(self, username: str):
        super().__init__(
            f"A registration request for '{username}' is already pending approval.", "USR_003")


class RegistrationNotFoundError(LibraryError):
    """Raised when an approval/rejection targets a non-existent registration."""
    def __init__(self, reg_id: str):
        super().__init__(f"Registration request '{reg_id}' not found.", "USR_004")


class OutstandingFineError(LibraryError):
    """Raised when a user with unpaid fines tries to borrow."""
    def __init__(self, amount: float):
        super().__init__(
            f"Outstanding fine of ₹{amount:.2f}. Please clear dues before borrowing.", "USR_005")


# ── Book Management ───────────────────────────────────────────────────────────

class BookNotFoundError(LibraryError):
    """Raised when a book_id is not found."""
    def __init__(self, book_id: str):
        super().__init__(f"Book '{book_id}' not found.", "BK_001")


class BookUnavailableError(LibraryError):
    """Raised when no copies of a book are available for borrowing."""
    def __init__(self, title: str):
        super().__init__(f"No copies of '{title}' are currently available.", "BK_002")


class BookStillBorrowedError(LibraryError):
    """Raised when trying to delete a book that has active borrows."""
    def __init__(self, title: str, borrowed: int):
        super().__init__(
            f"Cannot delete '{title}': {borrowed} copy/copies are still borrowed.", "BK_003")


class DuplicateISBNError(LibraryError):
    """Raised on duplicate ISBN — used informatively (copies are merged instead)."""
    def __init__(self, isbn: str):
        super().__init__(f"ISBN '{isbn}' already exists. Copies will be merged.", "BK_004")


class InvalidBookFieldError(LibraryError):
    """Raised when a book field fails validation."""
    def __init__(self, field: str, reason: str):
        super().__init__(f"Invalid value for '{field}': {reason}", "BK_005")


# ── Borrow / Return ───────────────────────────────────────────────────────────

class BorrowLimitExceededError(LibraryError):
    """Raised when a user exceeds their maximum borrow limit."""
    def __init__(self, limit: int):
        super().__init__(
            f"Borrow limit of {limit} book(s) reached. Return a book before borrowing more.", "BRW_001")


class RecordNotFoundError(LibraryError):
    """Raised when a borrow record_id is not found."""
    def __init__(self, record_id: str):
        super().__init__(f"Borrow record '{record_id}' not found.", "BRW_002")


class AlreadyReturnedError(LibraryError):
    """Raised when trying to return a book that was already returned."""
    def __init__(self, record_id: str):
        super().__init__(f"Record '{record_id}' has already been returned.", "BRW_003")


class UnauthorisedReturnError(LibraryError):
    """Raised when a user tries to return another user's book."""
    def __init__(self):
        super().__init__("You may only return books borrowed under your account.", "BRW_004")


# ── Reservation ───────────────────────────────────────────────────────────────

class ReservationNotFoundError(LibraryError):
    """Raised when a reservation_id is not found."""
    def __init__(self, reservation_id: str):
        super().__init__(f"Reservation '{reservation_id}' not found.", "RES_001")


class ReservationExpiredError(LibraryError):
    """Raised when an expired reservation is used."""
    def __init__(self, reservation_id: str):
        super().__init__(f"Reservation '{reservation_id}' has expired.", "RES_002")


# ── Fine Management ───────────────────────────────────────────────────────────

class FineOverpaymentError(LibraryError):
    """Raised when collected amount exceeds outstanding fine."""
    def __init__(self, collected: float, outstanding: float):
        super().__init__(
            f"Cannot collect ₹{collected:.2f}: outstanding fine is only ₹{outstanding:.2f}.", "FIN_001")


# ── Validation ────────────────────────────────────────────────────────────────

class ValidationError(LibraryError):
    """Raised when input data fails validation rules."""
    def __init__(self, field: str, reason: str):
        super().__init__(f"Validation failed for '{field}': {reason}", "VAL_001")


class WeakPasswordError(LibraryError):
    """Raised when a password does not meet strength requirements."""
    def __init__(self, reason: str):
        super().__init__(f"Password too weak: {reason}", "VAL_002")


# ── Persistence ───────────────────────────────────────────────────────────────

class SaveError(LibraryError):
    """Raised when the library state cannot be saved."""
    def __init__(self, filepath: str, reason: str):
        super().__init__(f"Could not save to '{filepath}': {reason}", "SAVE_001")


class LoadError(LibraryError):
    """Raised when the library state cannot be loaded."""
    def __init__(self, filepath: str, reason: str):
        super().__init__(f"Could not load from '{filepath}': {reason}", "LOAD_001")


# ── Import / Export ───────────────────────────────────────────────────────────

class ImportError(LibraryError):
    """Raised when a bulk import fails."""
    def __init__(self, filepath: str, reason: str):
        super().__init__(f"Import from '{filepath}' failed: {reason}", "IMP_001")


class ExportError(LibraryError):
    """Raised when a report export fails."""
    def __init__(self, filepath: str, reason: str):
        super().__init__(f"Export to '{filepath}' failed: {reason}", "EXP_001")
