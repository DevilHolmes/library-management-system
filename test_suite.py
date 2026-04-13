"""
tests/test_suite.py - Comprehensive Unit & Integration Tests

Run all tests:
    python -m pytest tests/test_suite.py -v
    # or without pytest:
    python tests/test_suite.py

Coverage:
    - Authentication & sessions
    - User management (CRUD, RBAC)
    - Self-registration & approval flow
    - Book management (add, update, delete, search, inventory)
    - Borrow / return lifecycle
    - Overdue fine calculation
    - Reservation creation
    - Fine collection & waiver
    - Recommendations engine
    - Analytics reports
    - Bulk CSV import
    - Report export
    - Persistence (save / load round-trip)
    - Config management
    - Validators
    - Custom exceptions
    - Audit trail
    - Session manager
"""

import sys
import os
import unittest
import tempfile
from datetime import date, timedelta

# Allow imports from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from library import LibrarySystem
from models import Role, BookStatus
from auth import has_permission, hash_password, verify_password
from config import Config, config
from validators import (validate_username, validate_password, validate_email,
                        validate_phone, validate_year, validate_copies,
                        validate_book_fields, validate_registration, password_strength)
from exceptions import (ValidationError, WeakPasswordError, BookNotFoundError,
                         UserNotFoundError, BorrowLimitExceededError)
from session_manager import SessionManager
from recommender import recommend_books
from analytics import overdue_report


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_lib() -> LibrarySystem:
    """Fresh library with notifications silenced."""
    lib = LibrarySystem("Test Library")
    lib.notifier.verbose = False
    return lib


def make_staff(lib, admin):
    return lib.create_user(admin, "staff1", "Staff@123", Role.STAFF,
                           "Staff One", "staff@lib.com", "9000000001")


def make_user(lib, admin, username="user1"):
    return lib.create_user(admin, username, "User@1234", Role.USER,
                           f"User {username}", f"{username}@mail.com", "9000000002")


def make_book(lib, actor, suffix="1"):
    return lib.add_book(actor, f"ISBN-{suffix}", f"Book {suffix}", f"Author {suffix}",
                        "Publisher", 2020, "Fiction", 3, "", "A1")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Authentication
# ─────────────────────────────────────────────────────────────────────────────

class TestAuthentication(unittest.TestCase):

    def setUp(self):
        self.lib = make_lib()

    def test_admin_default_login(self):
        admin = self.lib.login("admin", "Admin@123")
        self.assertIsNotNone(admin)
        self.assertEqual(admin.role, Role.ADMIN)

    def test_wrong_password_returns_none(self):
        result = self.lib.login("admin", "wrong")
        self.assertIsNone(result)

    def test_unknown_user_returns_none(self):
        result = self.lib.login("nobody", "pass")
        self.assertIsNone(result)

    def test_deactivated_user_cannot_login(self):
        admin = self.lib.login("admin", "Admin@123")
        user = make_user(self.lib, admin)
        user.is_active = False
        result = self.lib.login("user1", "User@1234")
        self.assertIsNone(result)

    def test_password_hashing(self):
        h = hash_password("secret")
        self.assertTrue(verify_password("secret", h))
        self.assertFalse(verify_password("wrong", h))


# ─────────────────────────────────────────────────────────────────────────────
# 2. RBAC — Permission Matrix
# ─────────────────────────────────────────────────────────────────────────────

class TestPermissions(unittest.TestCase):

    def setUp(self):
        self.lib = make_lib()
        self.admin = self.lib.login("admin", "Admin@123")
        self.staff = make_staff(self.lib, self.admin)
        self.user  = make_user(self.lib, self.admin)

    def test_admin_can_delete_book(self):
        self.assertTrue(has_permission(self.admin, "delete_book"))

    def test_staff_can_delete_book(self):
        self.assertTrue(has_permission(self.staff, "delete_book"))

    def test_user_cannot_delete_book(self):
        self.assertFalse(has_permission(self.user, "delete_book"))

    def test_user_can_view_inventory(self):
        self.assertTrue(has_permission(self.user, "view_inventory"))

    def test_user_cannot_generate_reports(self):
        self.assertFalse(has_permission(self.user, "generate_reports"))

    def test_user_cannot_create_user(self):
        self.assertFalse(has_permission(self.user, "create_user"))

    def test_staff_cannot_waive_fine(self):
        self.assertFalse(has_permission(self.staff, "waive_fine"))

    def test_admin_can_waive_fine(self):
        self.assertTrue(has_permission(self.admin, "waive_fine"))

    def test_permission_denied_raises(self):
        book = make_book(self.lib, self.staff)
        with self.assertRaises(PermissionError):
            self.lib.delete_book(self.user, book.book_id)

    def test_inactive_user_has_no_permissions(self):
        self.user.is_active = False
        self.assertFalse(has_permission(self.user, "borrow_book"))


# ─────────────────────────────────────────────────────────────────────────────
# 3. User Management
# ─────────────────────────────────────────────────────────────────────────────

class TestUserManagement(unittest.TestCase):

    def setUp(self):
        self.lib = make_lib()
        self.admin = self.lib.login("admin", "Admin@123")

    def test_create_user_success(self):
        u = make_user(self.lib, self.admin)
        self.assertEqual(u.username, "user1")
        self.assertEqual(u.role, Role.USER)

    def test_create_duplicate_username_raises(self):
        make_user(self.lib, self.admin)
        with self.assertRaises(ValueError):
            make_user(self.lib, self.admin)

    def test_staff_cannot_create_admin(self):
        staff = make_staff(self.lib, self.admin)
        with self.assertRaises(PermissionError):
            self.lib.create_user(staff, "newadmin", "Admin@123", Role.ADMIN,
                                 "New Admin", "a@b.com")

    def test_delete_user(self):
        u = make_user(self.lib, self.admin)
        uid = u.user_id
        self.lib.delete_user(self.admin, uid)
        self.assertNotIn(uid, self.lib._users)

    def test_cannot_delete_own_account(self):
        with self.assertRaises(ValueError):
            self.lib.delete_user(self.admin, self.admin.user_id)

    def test_toggle_user_status(self):
        u = make_user(self.lib, self.admin)
        self.assertTrue(u.is_active)
        self.lib.toggle_user_status(self.admin, u.user_id)
        self.assertFalse(u.is_active)
        self.lib.toggle_user_status(self.admin, u.user_id)
        self.assertTrue(u.is_active)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Self-Registration Flow
# ─────────────────────────────────────────────────────────────────────────────

class TestSelfRegistration(unittest.TestCase):

    def setUp(self):
        self.lib = make_lib()
        self.admin = self.lib.login("admin", "Admin@123")

    def test_register_creates_pending(self):
        reg_id = self.lib.register("newbie", "Pass@123", "New Bie", "n@b.com")
        self.assertIn(reg_id, self.lib._pending_registrations)

    def test_pending_user_cannot_login(self):
        self.lib.register("newbie", "Pass@123", "New Bie", "n@b.com")
        result = self.lib.login("newbie", "Pass@123")
        self.assertIsNone(result)

    def test_approve_registration(self):
        reg_id = self.lib.register("newbie", "Pass@123", "New Bie", "n@b.com")
        user = self.lib.approve_registration(self.admin, reg_id)
        self.assertNotIn(reg_id, self.lib._pending_registrations)
        result = self.lib.login("newbie", "Pass@123")
        self.assertIsNotNone(result)

    def test_reject_registration(self):
        reg_id = self.lib.register("newbie", "Pass@123", "New Bie", "n@b.com")
        self.lib.reject_registration(self.admin, reg_id)
        self.assertNotIn(reg_id, self.lib._pending_registrations)
        result = self.lib.login("newbie", "Pass@123")
        self.assertIsNone(result)

    def test_duplicate_pending_raises(self):
        self.lib.register("newbie", "Pass@123", "New Bie", "n@b.com")
        with self.assertRaises(ValueError):
            self.lib.register("newbie", "Pass@123", "New Bie", "n@b.com")

    def test_duplicate_username_raises(self):
        make_user(self.lib, self.admin, "existinguser")
        with self.assertRaises(ValueError):
            self.lib.register("existinguser", "Pass@123", "X", "x@x.com")


# ─────────────────────────────────────────────────────────────────────────────
# 5. Book Management
# ─────────────────────────────────────────────────────────────────────────────

class TestBookManagement(unittest.TestCase):

    def setUp(self):
        self.lib = make_lib()
        self.admin = self.lib.login("admin", "Admin@123")
        self.staff = make_staff(self.lib, self.admin)

    def test_add_book(self):
        b = make_book(self.lib, self.staff)
        self.assertIn(b.book_id, self.lib._books)
        self.assertEqual(b.total_copies, 3)
        self.assertEqual(b.available_copies, 3)

    def test_add_duplicate_isbn_merges_copies(self):
        b1 = make_book(self.lib, self.staff)
        b2 = self.lib.add_book(self.staff, "ISBN-1", "Book 1", "Author 1",
                                "Publisher", 2020, "Fiction", 2)
        self.assertEqual(b1.total_copies, 5)

    def test_delete_book(self):
        b = make_book(self.lib, self.staff)
        self.lib.delete_book(self.staff, b.book_id)
        self.assertNotIn(b.book_id, self.lib._books)

    def test_cannot_delete_borrowed_book(self):
        b = make_book(self.lib, self.staff)
        user = make_user(self.lib, self.admin)
        self.lib.borrow_book(user, b.book_id)
        with self.assertRaises(ValueError):
            self.lib.delete_book(self.staff, b.book_id)

    def test_update_book(self):
        b = make_book(self.lib, self.staff)
        self.lib.update_book(self.staff, b.book_id, title="Updated Title")
        self.assertEqual(b.title, "Updated Title")

    def test_search_by_title(self):
        make_book(self.lib, self.staff, "1")
        make_book(self.lib, self.staff, "2")
        user = make_user(self.lib, self.admin)
        results = self.lib.search_books(user, query="Book 1")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Book 1")

    def test_search_available_only(self):
        b1 = make_book(self.lib, self.staff, "1")
        b2 = make_book(self.lib, self.staff, "2")
        user = make_user(self.lib, self.admin)
        # Borrow all copies of b1
        for _ in range(b1.total_copies):
            u = make_user(self.lib, self.admin, f"borrower{_}")
            self.lib.borrow_book(u, b1.book_id)
        results = self.lib.search_books(user, available_only=True)
        ids = [r.book_id for r in results]
        self.assertNotIn(b1.book_id, ids)
        self.assertIn(b2.book_id, ids)

    def test_user_cannot_add_book(self):
        user = make_user(self.lib, self.admin)
        with self.assertRaises(PermissionError):
            make_book(self.lib, user)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Borrow & Return Lifecycle
# ─────────────────────────────────────────────────────────────────────────────

class TestBorrowReturn(unittest.TestCase):

    def setUp(self):
        self.lib = make_lib()
        self.admin = self.lib.login("admin", "Admin@123")
        self.staff = make_staff(self.lib, self.admin)
        self.user  = make_user(self.lib, self.admin)
        self.book  = make_book(self.lib, self.staff)

    def test_borrow_success(self):
        rec = self.lib.borrow_book(self.user, self.book.book_id)
        self.assertFalse(rec.is_returned)
        self.assertIn(self.book.book_id, self.user.borrowed_books)
        self.assertEqual(self.book.available_copies, 2)

    def test_return_success(self):
        rec = self.lib.borrow_book(self.user, self.book.book_id)
        self.lib.return_book(self.user, rec.record_id)
        self.assertTrue(rec.is_returned)
        self.assertNotIn(self.book.book_id, self.user.borrowed_books)
        self.assertEqual(self.book.available_copies, 3)

    def test_borrow_unavailable_raises(self):
        # Exhaust all copies
        for i in range(self.book.total_copies):
            u = make_user(self.lib, self.admin, f"extra{i}")
            self.lib.borrow_book(u, self.book.book_id)
        with self.assertRaises(ValueError):
            self.lib.borrow_book(self.user, self.book.book_id)

    def test_borrow_limit_enforced(self):
        books = [make_book(self.lib, self.staff, str(i)) for i in range(5)]
        for b in books[:3]:
            self.lib.borrow_book(self.user, b.book_id)
        with self.assertRaises(ValueError):
            self.lib.borrow_book(self.user, books[3].book_id)

    def test_double_return_raises(self):
        rec = self.lib.borrow_book(self.user, self.book.book_id)
        self.lib.return_book(self.user, rec.record_id)
        with self.assertRaises(ValueError):
            self.lib.return_book(self.user, rec.record_id)

    def test_staff_borrow_on_behalf(self):
        u2 = make_user(self.lib, self.admin, "u2")
        rec = self.lib.borrow_book(self.staff, self.book.book_id, borrower_id=u2.user_id)
        self.assertIn(self.book.book_id, u2.borrowed_books)

    def test_user_cannot_return_others_book(self):
        u2 = make_user(self.lib, self.admin, "u2")
        rec = self.lib.borrow_book(u2, self.book.book_id)
        with self.assertRaises(PermissionError):
            self.lib.return_book(self.user, rec.record_id)

    def test_outstanding_fine_blocks_borrow(self):
        self.user.fine_amount = 10.0
        with self.assertRaises(ValueError):
            self.lib.borrow_book(self.user, self.book.book_id)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Overdue Fines
# ─────────────────────────────────────────────────────────────────────────────

class TestOverdueFines(unittest.TestCase):

    def setUp(self):
        self.lib = make_lib()
        self.admin = self.lib.login("admin", "Admin@123")
        self.staff = make_staff(self.lib, self.admin)
        self.user  = make_user(self.lib, self.admin)
        self.book  = make_book(self.lib, self.staff)

    def test_on_time_return_no_fine(self):
        rec = self.lib.borrow_book(self.user, self.book.book_id)
        self.lib.return_book(self.user, rec.record_id)
        self.assertEqual(rec.fine, 0.0)

    def test_overdue_fine_calculated(self):
        rec = self.lib.borrow_book(self.user, self.book.book_id)
        rec.due_date = date.today() - timedelta(days=5)
        self.lib.return_book(self.user, rec.record_id)
        self.assertEqual(rec.fine, 25.0)   # 5 days × ₹5
        self.assertEqual(self.user.fine_amount, 25.0)

    def test_fine_blocks_future_borrow(self):
        rec = self.lib.borrow_book(self.user, self.book.book_id)
        rec.due_date = date.today() - timedelta(days=3)
        self.lib.return_book(self.user, rec.record_id)
        book2 = make_book(self.lib, self.staff, "2")
        with self.assertRaises(ValueError):
            self.lib.borrow_book(self.user, book2.book_id)

    def test_waive_fine(self):
        self.user.fine_amount = 50.0
        self.lib.waive_fine(self.admin, self.user.user_id)
        self.assertEqual(self.user.fine_amount, 0.0)

    def test_collect_fine_partial(self):
        self.user.fine_amount = 50.0
        self.lib.collect_fine(self.admin, self.user.user_id, 20.0)
        self.assertEqual(self.user.fine_amount, 30.0)

    def test_collect_overpayment_raises(self):
        self.user.fine_amount = 10.0
        with self.assertRaises(ValueError):
            self.lib.collect_fine(self.admin, self.user.user_id, 20.0)

    def test_overdue_report(self):
        rec = self.lib.borrow_book(self.user, self.book.book_id)
        rec.due_date = date.today() - timedelta(days=4)
        rows = overdue_report(self.lib)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][3], 4)    # days_overdue
        self.assertEqual(rows[0][4], 20.0) # fine 4×5


# ─────────────────────────────────────────────────────────────────────────────
# 8. Reservations
# ─────────────────────────────────────────────────────────────────────────────

class TestReservations(unittest.TestCase):

    def setUp(self):
        self.lib = make_lib()
        self.admin = self.lib.login("admin", "Admin@123")
        self.staff = make_staff(self.lib, self.admin)
        self.user  = make_user(self.lib, self.admin)
        self.book  = make_book(self.lib, self.staff)

    def test_reserve_success(self):
        res = self.lib.reserve_book(self.user, self.book.book_id)
        self.assertIn(res.reservation_id, self.lib._reservations)
        self.assertTrue(res.is_active)

    def test_reserve_nonexistent_book_raises(self):
        with self.assertRaises(ValueError):
            self.lib.reserve_book(self.user, "FAKE-ID")


# ─────────────────────────────────────────────────────────────────────────────
# 9. Recommendations
# ─────────────────────────────────────────────────────────────────────────────

class TestRecommendations(unittest.TestCase):

    def setUp(self):
        self.lib = make_lib()
        self.admin = self.lib.login("admin", "Admin@123")
        self.staff = make_staff(self.lib, self.admin)
        self.user  = make_user(self.lib, self.admin)

    def test_no_history_recommends_new_books(self):
        for i in range(5):
            make_book(self.lib, self.staff, str(i))
        recs = recommend_books(self.lib, self.user, top_n=3)
        self.assertLessEqual(len(recs), 3)

    def test_borrowed_books_excluded_from_recs(self):
        book = make_book(self.lib, self.staff)
        self.lib.borrow_book(self.user, book.book_id)
        recs = recommend_books(self.lib, self.user)
        self.assertNotIn(book, recs)

    def test_genre_affinity_boosts_score(self):
        # Add Fiction and Non-Fiction books; user borrows Fiction
        b_fiction = self.lib.add_book(self.staff, "F1", "Fiction A", "Aut", "Pub",
                                       2020, "Fiction", 3)
        b_nonfic  = self.lib.add_book(self.staff, "NF1", "NonFiction A", "Aut", "Pub",
                                       2020, "Non-Fiction", 3)
        b_fiction2 = self.lib.add_book(self.staff, "F2", "Fiction B", "Aut", "Pub",
                                        2020, "Fiction", 3)
        self.lib.borrow_book(self.user, b_fiction.book_id)
        rec = self.lib.return_book(self.user, list(self.lib._borrow_records.values())[-1].record_id)
        recs = recommend_books(self.lib, self.user, top_n=2)
        # Fiction B should rank above Non-Fiction A
        rec_ids = [r.book_id for r in recs]
        if b_fiction2.book_id in rec_ids and b_nonfic.book_id in rec_ids:
            self.assertLess(rec_ids.index(b_fiction2.book_id),
                            rec_ids.index(b_nonfic.book_id))


# ─────────────────────────────────────────────────────────────────────────────
# 10. Persistence
# ─────────────────────────────────────────────────────────────────────────────

class TestPersistence(unittest.TestCase):

    def test_save_and_load_roundtrip(self):
        from persistence import save_library, load_library
        lib = make_lib()
        admin = lib.login("admin", "Admin@123")
        staff = make_staff(lib, admin)
        book  = make_book(lib, staff)
        user  = make_user(lib, admin)
        lib.borrow_book(user, book.book_id)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            fp = f.name

        try:
            save_library(lib, fp)
            lib2 = load_library(fp)
            self.assertEqual(len(lib2._users), len(lib._users))
            self.assertEqual(len(lib2._books), len(lib._books))
            self.assertEqual(len(lib2._borrow_records), len(lib._borrow_records))
            # Verify data integrity
            u2 = next(u for u in lib2._users.values() if u.username == "user1")
            self.assertIn(book.book_id, u2.borrowed_books)
        finally:
            os.unlink(fp)

    def test_load_nonexistent_raises(self):
        from persistence import load_library
        with self.assertRaises(FileNotFoundError):
            load_library("/tmp/nonexistent_library.json")


# ─────────────────────────────────────────────────────────────────────────────
# 11. Validators
# ─────────────────────────────────────────────────────────────────────────────

class TestValidators(unittest.TestCase):

    def test_valid_username(self):
        self.assertEqual(validate_username("JohnDoe"), "johndoe")

    def test_username_too_short(self):
        with self.assertRaises(ValidationError):
            validate_username("ab")

    def test_username_invalid_chars(self):
        with self.assertRaises(ValidationError):
            validate_username("john doe!")

    def test_valid_email(self):
        self.assertEqual(validate_email("Test@Example.COM"), "test@example.com")

    def test_invalid_email(self):
        with self.assertRaises(ValidationError):
            validate_email("notanemail")

    def test_valid_year(self):
        self.assertEqual(validate_year("2020"), 2020)

    def test_invalid_year(self):
        with self.assertRaises(ValidationError):
            validate_year("999")

    def test_valid_copies(self):
        self.assertEqual(validate_copies("5"), 5)

    def test_zero_copies_raises(self):
        with self.assertRaises(ValidationError):
            validate_copies("0")

    def test_weak_password_length(self):
        cfg = Config()
        cfg.PASSWORD_MIN_LENGTH = 8
        with self.assertRaises(WeakPasswordError):
            validate_password("abc")

    def test_strong_password(self):
        self.assertEqual(validate_password("Secure1!"), "Secure1!")

    def test_password_strength_score(self):
        result = password_strength("Abc1!")
        self.assertIn("score", result)
        self.assertGreaterEqual(result["score"], 3)

    def test_validate_phone_empty_ok(self):
        self.assertEqual(validate_phone(""), "")

    def test_validate_phone_invalid(self):
        with self.assertRaises(ValidationError):
            validate_phone("12")

    def test_validate_book_fields(self):
        result = validate_book_fields("978-0-06-112008-4", "Title", "Author", 2020, 3, "Fiction")
        self.assertEqual(result["copies"], 3)
        self.assertEqual(result["year"], 2020)


# ─────────────────────────────────────────────────────────────────────────────
# 12. Session Manager
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionManager(unittest.TestCase):

    def setUp(self):
        self.sm = SessionManager()
        self.lib = make_lib()
        self.admin = self.lib.login("admin", "Admin@123")

    def test_create_and_validate_session(self):
        token = self.sm.create_session(self.admin)
        session = self.sm.validate_token(token)
        self.assertEqual(session.username, "admin")

    def test_invalid_token_raises(self):
        from exceptions import SessionExpiredError
        with self.assertRaises(SessionExpiredError):
            self.sm.validate_token("fake-token")

    def test_end_session(self):
        from exceptions import SessionExpiredError
        token = self.sm.create_session(self.admin)
        self.sm.end_session(token)
        with self.assertRaises(SessionExpiredError):
            self.sm.validate_token(token)

    def test_max_sessions_evicts_oldest(self):
        from config import config as cfg
        original = cfg.MAX_SESSIONS_PER_USER
        cfg.MAX_SESSIONS_PER_USER = 2
        try:
            t1 = self.sm.create_session(self.admin)
            t2 = self.sm.create_session(self.admin)
            t3 = self.sm.create_session(self.admin)  # should evict t1
            # t1 should no longer be valid
            from exceptions import SessionExpiredError
            with self.assertRaises(SessionExpiredError):
                self.sm.validate_token(t1)
            self.sm.validate_token(t2)
            self.sm.validate_token(t3)
        finally:
            cfg.MAX_SESSIONS_PER_USER = original


# ─────────────────────────────────────────────────────────────────────────────
# 13. Bulk CSV Import
# ─────────────────────────────────────────────────────────────────────────────

class TestBulkImport(unittest.TestCase):

    def setUp(self):
        self.lib = make_lib()
        self.admin = self.lib.login("admin", "Admin@123")
        self.staff = make_staff(self.lib, self.admin)

    def test_import_sample_csv(self):
        from book_import import generate_sample_csv, import_books_csv
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            fp = f.name

        try:
            generate_sample_csv(fp)
            result = import_books_csv(self.lib, self.staff, fp)
            self.assertGreater(result.imported, 0)
            self.assertEqual(result.failed, 0)
        finally:
            os.unlink(fp)

    def test_import_skips_duplicates(self):
        from book_import import import_books_csv
        import csv as csv_mod

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False,
                                         mode="w", newline="") as f:
            fp = f.name
            w = csv_mod.writer(f)
            w.writerow(["isbn","title","author","publisher","year","genre","copies"])
            w.writerow(["DUP-001","Dup Book","Author","Pub","2020","Fiction","2"])

        try:
            import_books_csv(self.lib, self.staff, fp, skip_duplicates=True)
            count_before = len(self.lib._books)
            import_books_csv(self.lib, self.staff, fp, skip_duplicates=True)
            self.assertEqual(len(self.lib._books), count_before)
        finally:
            os.unlink(fp)

    def test_import_invalid_row_counted_as_failed(self):
        from book_import import import_books_csv
        import csv as csv_mod

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False,
                                         mode="w", newline="") as f:
            fp = f.name
            w = csv_mod.writer(f)
            w.writerow(["isbn","title","author","publisher","year","genre","copies"])
            w.writerow(["","","","","notayear","","0"])  # all invalid

        try:
            result = import_books_csv(self.lib, self.staff, fp)
            self.assertGreater(result.failed, 0)
        finally:
            os.unlink(fp)


# ─────────────────────────────────────────────────────────────────────────────
# 14. Report Export
# ─────────────────────────────────────────────────────────────────────────────

class TestReportExport(unittest.TestCase):

    def setUp(self):
        self.lib = make_lib()
        self.admin = self.lib.login("admin", "Admin@123")
        self.staff = make_staff(self.lib, self.admin)
        make_book(self.lib, self.staff)
        make_user(self.lib, self.admin)

    def _tmpdir(self):
        d = tempfile.mkdtemp()
        return d

    def test_export_books_csv(self):
        from reports_export import export_books_csv
        d = self._tmpdir()
        fp = export_books_csv(self.lib, self.admin, d)
        self.assertTrue(os.path.exists(fp))
        self.assertGreater(os.path.getsize(fp), 0)

    def test_export_users_csv(self):
        from reports_export import export_users_csv
        d = self._tmpdir()
        fp = export_users_csv(self.lib, self.admin, d)
        self.assertTrue(os.path.exists(fp))

    def test_export_inventory_txt(self):
        from reports_export import export_inventory_txt
        d = self._tmpdir()
        fp = export_inventory_txt(self.lib, self.admin, d)
        self.assertTrue(os.path.exists(fp))

    def test_export_all(self):
        from reports_export import export_all
        d = self._tmpdir()
        out = export_all(self.lib, self.admin, d)
        self.assertTrue(os.path.isdir(out))
        self.assertGreater(len(os.listdir(out)), 0)

    def test_user_cannot_export(self):
        from reports_export import export_books_csv
        from exceptions import PermissionDeniedError
        user = make_user(self.lib, self.admin, "export_user")
        with self.assertRaises(PermissionDeniedError):
            export_books_csv(self.lib, user, self._tmpdir())


# ─────────────────────────────────────────────────────────────────────────────
# 15. Audit Trail
# ─────────────────────────────────────────────────────────────────────────────

class TestAuditTrail(unittest.TestCase):

    def setUp(self):
        self.lib = make_lib()
        self.admin = self.lib.login("admin", "Admin@123")
        self.staff = make_staff(self.lib, self.admin)
        self.user  = make_user(self.lib, self.admin)
        book = make_book(self.lib, self.staff)
        self.lib.borrow_book(self.user, book.book_id)

    def test_entries_populated(self):
        from audit import AuditTrail
        trail = AuditTrail(self.lib)
        entries = trail.filter()
        self.assertGreater(len(entries), 0)

    def test_filter_by_actor(self):
        from audit import AuditTrail
        trail = AuditTrail(self.lib)
        entries = trail.filter(actor="admin")
        self.assertTrue(all(e.actor == "admin" for e in entries))

    def test_filter_by_action(self):
        from audit import AuditTrail
        trail = AuditTrail(self.lib)
        entries = trail.filter(action="BORROW")
        self.assertTrue(all(e.action == "BORROW" for e in entries))

    def test_export_csv(self):
        from audit import AuditTrail
        trail = AuditTrail(self.lib)
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            fp = f.name
        try:
            trail.export_csv(fp)
            self.assertTrue(os.path.exists(fp))
            self.assertGreater(os.path.getsize(fp), 0)
        finally:
            os.unlink(fp)


# ─────────────────────────────────────────────────────────────────────────────
# 16. Config Management
# ─────────────────────────────────────────────────────────────────────────────

class TestConfig(unittest.TestCase):

    def test_default_values(self):
        c = Config()
        self.assertEqual(c.BORROW_DURATION_DAYS, 14)
        self.assertEqual(c.FINE_PER_DAY, 5.0)
        self.assertEqual(c.MAX_BOOKS_USER, 3)

    def test_update(self):
        c = Config()
        c.update(FINE_PER_DAY=10.0)
        self.assertEqual(c.FINE_PER_DAY, 10.0)

    def test_update_unknown_key_raises(self):
        c = Config()
        with self.assertRaises(ValueError):
            c.update(NONEXISTENT_KEY=99)

    def test_save_and_load_config(self):
        from config import save_config, load_config, reset_config, config as cfg
        original = cfg.FINE_PER_DAY
        cfg.FINE_PER_DAY = 99.0
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            fp = f.name
        try:
            save_config(fp)
            reset_config()
            load_config(fp)
            from config import config as cfg2
            self.assertEqual(cfg2.FINE_PER_DAY, 99.0)
        finally:
            os.unlink(fp)
            reset_config()


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    test_classes = [
        TestAuthentication,
        TestPermissions,
        TestUserManagement,
        TestSelfRegistration,
        TestBookManagement,
        TestBorrowReturn,
        TestOverdueFines,
        TestReservations,
        TestRecommendations,
        TestPersistence,
        TestValidators,
        TestSessionManager,
        TestBulkImport,
        TestReportExport,
        TestAuditTrail,
        TestConfig,
    ]

    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
