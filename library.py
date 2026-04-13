"""
library.py - Core Library Management Service
"""

import uuid
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict
from models import User, Book, BorrowRecord, Reservation, Role, BookStatus
from auth import require_permission, hash_password, verify_password, has_permission
from notifications import NotificationService


BORROW_DURATION_DAYS = 14      # 2-week borrow period
FINE_PER_DAY = 5.0             # ₹5 per day overdue
MAX_BOOKS_PER_USER = 3         # max books a regular user can borrow
RESERVATION_EXPIRY_HOURS = 48  # reservation expires after 48 hours


class LibrarySystem:
    """Central Library Management System with Role-Based Access Control."""

    def __init__(self, library_name: str = "City Public Library"):
        self.library_name = library_name
        self._users: Dict[str, User] = {}           # user_id -> User
        self._books: Dict[str, Book] = {}           # book_id -> Book
        self._borrow_records: Dict[str, BorrowRecord] = {}
        self._reservations: Dict[str, Reservation] = {}
        self._pending_registrations: Dict[str, dict] = {}  # reg_id -> request dict
        self._logs: List[dict] = []
        self.notifier = NotificationService(verbose=True)
        self._setup_default_admin()

    # ─── Setup ─────────────────────────────────────────────────────────────────

    def _setup_default_admin(self):
        admin = User(
            user_id="U-ADMIN-001",
            username="admin",
            password_hash=hash_password("Admin@123"),
            role=Role.ADMIN,
            full_name="System Administrator",
            email="admin@library.com",
            phone="9999999999",
        )
        self._users[admin.user_id] = admin

    def _log(self, actor: str, action: str, detail: str):
        self._logs.append({
            "timestamp": datetime.now().isoformat(),
            "actor": actor,
            "action": action,
            "detail": detail,
        })

    def _generate_id(self, prefix: str) -> str:
        return f"{prefix}-{str(uuid.uuid4())[:8].upper()}"

    # ─── Authentication ────────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> Optional[User]:
        for user in self._users.values():
            if user.username == username:
                if not user.is_active:
                    print(f"⚠️  Account '{username}' is deactivated.")
                    return None
                if verify_password(password, user.password_hash):
                    self._log(username, "LOGIN", "Successful login")
                    print(f"✅ Welcome, {user.full_name}! [{user.role.value.upper()}]")
                    return user
                else:
                    self._log(username, "LOGIN_FAIL", "Wrong password")
                    print("❌ Incorrect password.")
                    return None
        print(f"❌ User '{username}' not found.")
        return None

    # ─── Self-Registration ───────────────────────────────────────────────────

    def register(self, username: str, password: str, full_name: str,
                 email: str, phone: str = "") -> str:
        """Public self-registration — creates a pending request for admin approval."""
        for u in self._users.values():
            if u.username == username:
                raise ValueError(f"Username '{username}' is already taken.")
        for req in self._pending_registrations.values():
            if req["username"] == username:
                raise ValueError(f"A registration request for '{username}' is already pending.")

        reg_id = self._generate_id("REG")
        self._pending_registrations[reg_id] = {
            "reg_id": reg_id,
            "username": username,
            "password_hash": hash_password(password),
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "requested_at": datetime.now().isoformat(),
        }
        self._log("(public)", "REGISTER_REQUEST", f"New request from '{username}' ({email})")
        self.notifier.send_registration_received(full_name, email)
        print(f"✅ Registration request submitted for '{username}'.")
        print(f"   Request ID: {reg_id}  |  Awaiting admin approval.")
        return reg_id

    @require_permission("create_user")
    def list_pending_registrations(self, current_user: User):
        """Admin views all pending registration requests."""
        reqs = list(self._pending_registrations.values())
        if not reqs:
            print("  ℹ️  No pending registration requests.")
            return
        print(f"\n{'─'*80}")
        print(f"  📥 PENDING REGISTRATION REQUESTS ({len(reqs)})")
        print(f"{'─'*80}")
        print(f"  {'Reg ID':<14} {'Username':<16} {'Full Name':<20} {'Email':<25} Requested At")
        print(f"  {'─'*76}")
        for r in reqs:
            ts = r["requested_at"][:19]
            print(f"  {r['reg_id']:<14} {r['username']:<16} {r['full_name']:<20} {r['email']:<25} {ts}")
        print(f"{'─'*80}\n")

    @require_permission("create_user")
    def approve_registration(self, current_user: User, reg_id: str) -> User:
        """Admin approves a pending registration — activates the account."""
        req = self._pending_registrations.get(reg_id)
        if not req:
            raise ValueError(f"Registration request '{reg_id}' not found.")
        user = User(
            user_id=self._generate_id("U"),
            username=req["username"],
            password_hash=req["password_hash"],
            role=Role.USER,
            full_name=req["full_name"],
            email=req["email"],
            phone=req["phone"],
            is_active=True,
        )
        self._users[user.user_id] = user
        del self._pending_registrations[reg_id]
        self._log(current_user.username, "APPROVE_REG",
                  f"Approved '{req['username']}' -> user_id={user.user_id}")
        self.notifier.send_welcome(user.full_name, user.username, user.email)
        print(f"✅ Registration approved! '{user.username}' is now an active user. ID: {user.user_id}")
        return user

    @require_permission("create_user")
    def reject_registration(self, current_user: User, reg_id: str):
        """Admin rejects a pending registration request."""
        req = self._pending_registrations.pop(reg_id, None)
        if not req:
            raise ValueError(f"Registration request '{reg_id}' not found.")
        self._log(current_user.username, "REJECT_REG", f"Rejected request from '{req['username']}'")
        self.notifier.send_registration_rejected(req["full_name"], req["email"])
        print(f"🗑️  Registration request from '{req['username']}' rejected.")

    # ─── User Management ──────────────────────────────────────────────────────

    @require_permission("create_user")
    def create_user(self, current_user: User, username: str, password: str,
                    role: Role, full_name: str, email: str, phone: str = "") -> User:
        # Prevent non-admins from creating admin accounts
        if role == Role.ADMIN and current_user.role != Role.ADMIN:
            raise PermissionError("Only admins can create admin accounts.")

        for u in self._users.values():
            if u.username == username:
                raise ValueError(f"Username '{username}' already exists.")

        user = User(
            user_id=self._generate_id("U"),
            username=username,
            password_hash=hash_password(password),
            role=role,
            full_name=full_name,
            email=email,
            phone=phone,
        )
        self._users[user.user_id] = user
        self._log(current_user.username, "CREATE_USER", f"Created {role.value}: {username}")
        print(f"✅ User '{username}' ({role.value}) created. ID: {user.user_id}")
        return user

    @require_permission("delete_user")
    def delete_user(self, current_user: User, user_id: str):
        if user_id not in self._users:
            raise ValueError(f"User {user_id} not found.")
        if user_id == current_user.user_id:
            raise ValueError("Cannot delete your own account.")
        target = self._users.pop(user_id)
        self._log(current_user.username, "DELETE_USER", f"Deleted {target.username}")
        print(f"🗑️  User '{target.username}' deleted.")

    @require_permission("view_all_users")
    def list_users(self, current_user: User, role_filter: Optional[Role] = None):
        users = list(self._users.values())
        if role_filter:
            users = [u for u in users if u.role == role_filter]
        print(f"\n{'─'*70}")
        print(f"{'ID':<15} {'Username':<15} {'Role':<10} {'Name':<20} {'Active'}")
        print(f"{'─'*70}")
        for u in users:
            active = "✅" if u.is_active else "❌"
            print(f"{u.user_id:<15} {u.username:<15} {u.role.value:<10} {u.full_name:<20} {active}")
        print(f"{'─'*70}")
        print(f"Total: {len(users)} user(s)\n")

    @require_permission("update_any_user")
    def toggle_user_status(self, current_user: User, user_id: str):
        user = self._users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found.")
        user.is_active = not user.is_active
        status = "activated" if user.is_active else "deactivated"
        self._log(current_user.username, "TOGGLE_USER", f"{status} {user.username}")
        print(f"✅ User '{user.username}' has been {status}.")

    # ─── Book Management ──────────────────────────────────────────────────────

    @require_permission("add_book")
    def add_book(self, current_user: User, isbn: str, title: str, author: str,
                 publisher: str, year: int, genre: str, copies: int,
                 description: str = "", location: str = "") -> Book:
        # Check if ISBN already exists
        for b in self._books.values():
            if b.isbn == isbn:
                b.total_copies += copies
                b.available_copies += copies
                self._log(current_user.username, "ADD_COPIES", f"+{copies} to '{title}'")
                print(f"📚 Added {copies} more copies of '{title}'. Total: {b.total_copies}")
                return b

        book = Book(
            book_id=self._generate_id("B"),
            isbn=isbn,
            title=title,
            author=author,
            publisher=publisher,
            year=year,
            genre=genre,
            total_copies=copies,
            available_copies=copies,
            description=description,
            location=location,
        )
        self._books[book.book_id] = book
        self._log(current_user.username, "ADD_BOOK", f"Added '{title}' ({copies} copies)")
        print(f"✅ Book '{title}' added. ID: {book.book_id}")
        return book

    @require_permission("delete_book")
    def delete_book(self, current_user: User, book_id: str):
        book = self._books.get(book_id)
        if not book:
            raise ValueError(f"Book {book_id} not found.")
        if book.available_copies < book.total_copies:
            raise ValueError("Cannot delete: some copies are currently borrowed.")
        self._books.pop(book_id)
        self._log(current_user.username, "DELETE_BOOK", f"Deleted '{book.title}'")
        print(f"🗑️  Book '{book.title}' deleted.")

    @require_permission("update_book")
    def update_book(self, current_user: User, book_id: str, **kwargs):
        book = self._books.get(book_id)
        if not book:
            raise ValueError(f"Book {book_id} not found.")
        allowed = {"title", "author", "publisher", "year", "genre", "description", "location", "status"}
        for key, val in kwargs.items():
            if key in allowed:
                setattr(book, key, val)
        self._log(current_user.username, "UPDATE_BOOK", f"Updated '{book.title}'")
        print(f"✅ Book '{book.title}' updated.")

    @require_permission("view_all_books")
    def search_books(self, current_user: User, query: str = "",
                     genre: str = "", available_only: bool = False) -> List[Book]:
        results = list(self._books.values())
        q = query.lower()
        if q:
            results = [b for b in results if
                       q in b.title.lower() or q in b.author.lower() or
                       q in b.isbn or q in b.genre.lower()]
        if genre:
            results = [b for b in results if genre.lower() in b.genre.lower()]
        if available_only:
            results = [b for b in results if b.available_copies > 0]

        print(f"\n{'─'*90}")
        print(f"{'ID':<12} {'Title':<30} {'Author':<20} {'Genre':<12} {'Avail/Total':<12} {'Status'}")
        print(f"{'─'*90}")
        for b in results:
            avail = f"{b.available_copies}/{b.total_copies}"
            print(f"{b.book_id:<12} {b.title[:28]:<30} {b.author[:18]:<20} {b.genre[:10]:<12} {avail:<12} {b.status.value}")
        print(f"{'─'*90}")
        print(f"Found: {len(results)} book(s)\n")
        return results

    @require_permission("view_inventory")
    def view_inventory(self, current_user: User):
        print(f"\n{'='*90}")
        print(f"  📦 INVENTORY REPORT — {self.library_name}")
        print(f"{'='*90}")
        total_books = len(self._books)
        total_copies = sum(b.total_copies for b in self._books.values())
        available = sum(b.available_copies for b in self._books.values())
        borrowed = total_copies - available
        print(f"  Total Titles   : {total_books}")
        print(f"  Total Copies   : {total_copies}")
        print(f"  Available      : {available}")
        print(f"  Borrowed       : {borrowed}")
        print(f"\n  By Genre:")
        genres: Dict[str, int] = {}
        for b in self._books.values():
            genres[b.genre] = genres.get(b.genre, 0) + b.total_copies
        for g, cnt in sorted(genres.items()):
            print(f"    {g:<20}: {cnt} copies")
        print(f"{'='*90}\n")

    # ─── Borrow / Return ──────────────────────────────────────────────────────

    @require_permission("borrow_book")
    def borrow_book(self, current_user: User, book_id: str,
                    borrower_id: Optional[str] = None) -> BorrowRecord:
        # Staff/admin can borrow on behalf of another user
        if borrower_id and has_permission(current_user, "process_return"):
            borrower = self._users.get(borrower_id)
            if not borrower:
                raise ValueError(f"User {borrower_id} not found.")
        else:
            borrower = current_user

        book = self._books.get(book_id)
        if not book:
            raise ValueError(f"Book {book_id} not found.")
        if book.available_copies <= 0:
            raise ValueError(f"No copies of '{book.title}' available.")

        # Check borrow limit for regular users
        if borrower.role == Role.USER and len(borrower.borrowed_books) >= MAX_BOOKS_PER_USER:
            raise ValueError(f"Borrow limit reached ({MAX_BOOKS_PER_USER} books max).")

        if borrower.fine_amount > 0:
            raise ValueError(f"Outstanding fine ₹{borrower.fine_amount:.2f}. Please clear dues first.")

        record = BorrowRecord(
            record_id=self._generate_id("R"),
            user_id=borrower.user_id,
            book_id=book_id,
            borrow_date=date.today(),
            due_date=date.today() + timedelta(days=BORROW_DURATION_DAYS),
        )
        self._borrow_records[record.record_id] = record
        borrower.borrowed_books.append(book_id)
        book.available_copies -= 1
        if book.available_copies == 0:
            book.status = BookStatus.BORROWED

        self._log(current_user.username, "BORROW",
                  f"{borrower.username} borrowed '{book.title}' due {record.due_date}")
        self.notifier.send_borrow_confirmation(
            borrower.full_name, borrower.email, book.title, record.due_date)
        print(f"✅ '{book.title}' borrowed by {borrower.full_name}")
        print(f"   Due date: {record.due_date}  |  Record ID: {record.record_id}")
        return record

    @require_permission("return_book")
    def return_book(self, current_user: User, record_id: str) -> BorrowRecord:
        record = self._borrow_records.get(record_id)
        if not record:
            raise ValueError(f"Borrow record {record_id} not found.")
        if record.is_returned:
            raise ValueError("This book has already been returned.")

        # Regular users can only return their own books
        if current_user.role == Role.USER and record.user_id != current_user.user_id:
            raise PermissionError("You can only return your own books.")

        book = self._books.get(record.book_id)
        borrower = self._users.get(record.user_id)
        today = date.today()

        # Calculate fine
        if today > record.due_date:
            overdue_days = (today - record.due_date).days
            record.fine = overdue_days * FINE_PER_DAY
            if borrower:
                borrower.fine_amount += record.fine
            print(f"⚠️  Overdue by {overdue_days} days. Fine: ₹{record.fine:.2f}")

        record.return_date = today
        record.is_returned = True

        if book:
            book.available_copies += 1
            book.status = BookStatus.AVAILABLE
        if borrower and record.book_id in borrower.borrowed_books:
            borrower.borrowed_books.remove(record.book_id)

        self._log(current_user.username, "RETURN",
                  f"Returned '{book.title if book else record.book_id}' fine=₹{record.fine}")
        if borrower:
            self.notifier.send_return_confirmation(
                borrower.full_name, borrower.email,
                book.title if book else record.book_id, record.fine)
        print(f"✅ Book returned successfully. Fine: ₹{record.fine:.2f}")
        return record

    # ─── Reservations ─────────────────────────────────────────────────────────

    @require_permission("reserve_book")
    def reserve_book(self, current_user: User, book_id: str) -> Reservation:
        book = self._books.get(book_id)
        if not book:
            raise ValueError(f"Book {book_id} not found.")
        if book.available_copies > 0:
            print(f"ℹ️  '{book.title}' is available now. Consider borrowing directly.")

        reservation = Reservation(
            reservation_id=self._generate_id("RES"),
            user_id=current_user.user_id,
            book_id=book_id,
            expires_at=datetime.now() + timedelta(hours=RESERVATION_EXPIRY_HOURS),
        )
        self._reservations[reservation.reservation_id] = reservation
        self._log(current_user.username, "RESERVE", f"Reserved '{book.title}'")
        print(f"✅ Reservation created. ID: {reservation.reservation_id}")
        print(f"   Expires at: {reservation.expires_at.strftime('%Y-%m-%d %H:%M')}")
        return reservation

    # ─── Borrow History ───────────────────────────────────────────────────────

    @require_permission("view_borrow_history")
    def view_all_borrow_history(self, current_user: User, active_only: bool = False):
        records = list(self._borrow_records.values())
        if active_only:
            records = [r for r in records if not r.is_returned]
        self._print_records(records, "ALL BORROW HISTORY")

    def view_my_history(self, current_user: User):
        records = [r for r in self._borrow_records.values()
                   if r.user_id == current_user.user_id]
        self._print_records(records, f"MY BORROW HISTORY — {current_user.full_name}")

    def _print_records(self, records: List[BorrowRecord], title: str):
        print(f"\n{'='*95}")
        print(f"  📋 {title}")
        print(f"{'='*95}")
        print(f"{'Record ID':<14} {'User ID':<12} {'Book ID':<12} {'Borrowed':<12} {'Due':<12} {'Returned':<12} {'Fine':<8} {'Status'}")
        print(f"{'─'*95}")
        for r in records:
            returned = str(r.return_date) if r.return_date else "—"
            status = "✅ Returned" if r.is_returned else "📖 Active"
            print(f"{r.record_id:<14} {r.user_id:<12} {r.book_id:<12} "
                  f"{str(r.borrow_date):<12} {str(r.due_date):<12} {returned:<12} ₹{r.fine:<6.1f} {status}")
        print(f"{'='*95}")
        print(f"Total records: {len(records)}\n")

    # ─── Fine Management ──────────────────────────────────────────────────────

    @require_permission("waive_fine")
    def waive_fine(self, current_user: User, user_id: str):
        user = self._users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found.")
        amount = user.fine_amount
        user.fine_amount = 0.0
        self._log(current_user.username, "WAIVE_FINE",
                  f"Waived ₹{amount:.2f} for {user.username}")
        print(f"✅ Fine of ₹{amount:.2f} waived for '{user.username}'.")

    @require_permission("collect_fine")
    def collect_fine(self, current_user: User, user_id: str, amount: float):
        user = self._users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found.")
        if amount > user.fine_amount:
            raise ValueError(f"Amount exceeds outstanding fine ₹{user.fine_amount:.2f}")
        user.fine_amount -= amount
        self._log(current_user.username, "COLLECT_FINE",
                  f"Collected ₹{amount:.2f} from {user.username}")
        self.notifier.send_fine_receipt(user.full_name, user.email, amount, user.fine_amount)
        print(f"✅ ₹{amount:.2f} collected. Remaining: ₹{user.fine_amount:.2f}")

    # ─── Reports ──────────────────────────────────────────────────────────────

    @require_permission("generate_reports")
    def generate_report(self, current_user: User):
        total_users = len(self._users)
        total_books = len(self._books)
        total_records = len(self._borrow_records)
        active_borrows = sum(1 for r in self._borrow_records.values() if not r.is_returned)
        total_fines = sum(u.fine_amount for u in self._users.values())
        overdue = [r for r in self._borrow_records.values()
                   if not r.is_returned and r.due_date < date.today()]

        print(f"\n{'='*60}")
        print(f"  📊 LIBRARY REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*60}")
        print(f"  Users          : {total_users}")
        print(f"  Book Titles    : {total_books}")
        print(f"  Total Borrows  : {total_records}")
        print(f"  Active Borrows : {active_borrows}")
        print(f"  Overdue Books  : {len(overdue)}")
        print(f"  Outstanding    : ₹{total_fines:.2f}")
        print(f"{'='*60}\n")

    @require_permission("view_reports")
    def send_overdue_alerts(self, current_user: User):
        """Scan all active borrows, send overdue notifications, return count."""
        from analytics import overdue_report
        rows = overdue_report(self)
        if not rows:
            print("  ✅ No overdue books — nothing to alert.")
            return 0
        print(f"  🔔 Sending overdue alerts for {len(rows)} borrow(s)...")
        for r, user, book, days, fine in rows:
            if user and book:
                self.notifier.send_overdue_alert(
                    user.full_name, user.email, user.phone,
                    book.title, days, fine)
        self._log(current_user.username, "OVERDUE_ALERTS",
                  f"Sent {len(rows)} overdue alert(s)")
        print(f"  ✅ {len(rows)} alert(s) dispatched.")
        return len(rows)

    @require_permission("view_reports")
    def send_due_soon_reminders(self, current_user: User, within_days: int = 3):
        """Send due-soon reminders for borrows expiring within `within_days`."""
        from datetime import date, timedelta
        today = date.today()
        cutoff = today + timedelta(days=within_days)
        rows = [
            (r, self._users.get(r.user_id), self._books.get(r.book_id))
            for r in self._borrow_records.values()
            if not r.is_returned and today <= r.due_date <= cutoff
        ]
        if not rows:
            print(f"  ✅ No borrows due within {within_days} day(s).")
            return 0
        print(f"  🔔 Sending due-soon reminders for {len(rows)} borrow(s)...")
        for r, user, book in rows:
            if user and book:
                days_left = (r.due_date - today).days
                self.notifier.send_due_reminder(
                    user.full_name, user.email, book.title, r.due_date, days_left)
        self._log(current_user.username, "DUE_REMINDERS",
                  f"Sent {len(rows)} due-soon reminder(s)")
        print(f"  ✅ {len(rows)} reminder(s) dispatched.")
        return len(rows)

    def get_recommendations(self, current_user: User, top_n: int = 5):
        """Print personalised book recommendations for the current user."""
        from recommender import print_recommendations
        print_recommendations(self, current_user, top_n)

    @require_permission("view_reports")
    def view_notification_log(self, current_user: User, last_n: int = 20):
        self.notifier.print_log(last_n)

    @require_permission("generate_reports")
    def full_dashboard(self, current_user: User):
        from analytics import full_dashboard
        full_dashboard(self)

    @require_permission("view_reports")
    def view_overdue_report(self, current_user: User):
        from analytics import print_overdue_report
        print_overdue_report(self)

    @require_permission("view_reports")
    def view_due_soon(self, current_user: User, within_days: int = 3):
        from analytics import print_due_soon_report
        print_due_soon_report(self, within_days)

    @require_permission("view_logs")
    def view_logs(self, current_user: User, last_n: int = 20):
        print(f"\n{'─'*80}")
        print(f"  🗒️  SYSTEM LOGS (last {last_n})")
        print(f"{'─'*80}")
        for entry in self._logs[-last_n:]:
            ts = entry["timestamp"][:19]
            print(f"  [{ts}] {entry['actor']:<12} | {entry['action']:<15} | {entry['detail']}")
        print(f"{'─'*80}\n")
