# Library Management System

A feature-rich, terminal-based Library Management System written in pure Python — no external dependencies required. It supports role-based access control, book circulation, fine management, analytics, notifications, recommendations, and persistent JSON storage.

---

##  Features

###  User & Access Management
- Three roles: **Admin**, **Staff**, and **User** — each with a distinct permission set
- Self-registration workflow with admin approval/rejection queue
- Secure password hashing (SHA-256 + salt, no external libraries)
- Configurable password strength policy (length, uppercase, digits, special chars)
- Session tracking with configurable timeout and per-user session limits

###  Book Catalogue & Circulation
- Add, update, delete, and search books (by title, author, ISBN, or genre)
- Multi-copy tracking — available vs. total copies updated automatically
- Borrow and return books with automatic due-date calculation (default: 14 days)
- Book reservations with 48-hour expiry
- Bulk import books from a CSV file
- Staff can borrow on behalf of users

###  Fine Management
- Automatic fine accrual on overdue returns (₹5/day by default)
- Fine collection (partial payments supported)
- Admin-only fine waiver
- Outstanding fine check blocks new borrows

###  Analytics Dashboard
- Overdue report with accrued fine totals
- Due-soon report (configurable look-ahead window)
- Top borrowed books & most active borrowers
- Genre distribution with popularity index
- Monthly borrow/return activity
- Inventory health (utilisation bar)

###  Notifications (Simulated)
- Email and SMS notifications for: registration, borrow, return, overdue alerts, due-soon reminders, fine receipts
- In-memory notification log viewable from the admin panel
- Verbose/silent mode toggle

###  Book Recommendations
- Personalised recommendations based on genre affinity, author affinity, global popularity, and recency
- Excludes books already borrowed or currently held

###  Persistence
- Full library state (users, books, records, reservations, logs) saved to and loaded from JSON
- Auto-save on CLI exit
- Config saved/loaded separately as `library_config.json`

###  Audit Trail
- Structured audit log with filtering by actor, action, category, and date range
- Export audit log to CSV or plain text
- Audit summary statistics

###  Report Exports
- Export books, users, borrow records, overdue list, fines, and inventory to CSV/TXT
- Timestamped export folders for full snapshots

---

##  Project Structure

```
.
├── library.py           # Core LibrarySystem class — the central service layer
├── models.py            # Data models: User, Book, BorrowRecord, Reservation
├── auth.py              # Password hashing, RBAC permissions, @require_permission decorator
├── cli.py               # Interactive command-line interface
├── gui.py               # (Optional) GUI interface
├── config.py            # System-wide configuration & Config singleton
├── validators.py        # Input validation for all fields
├── exceptions.py        # Custom exception hierarchy
├── persistence.py       # JSON save/load for full library state
├── analytics.py         # Reporting functions & dashboard
├── audit.py             # Structured audit trail with filtering and export
├── notifications.py     # Simulated email/SMS notification service
├── recommender.py       # Personalised book recommendation engine
├── reports_export.py    # CSV/TXT report export utilities
├── session_manager.py   # Multi-session tracking with timeout enforcement
├── book_import.py       # Bulk CSV book import
└── demo.py              # Full-feature demonstration script
```

---

##  Getting Started

### Prerequisites
- Python **3.10+**
- No third-party packages required

### Run the CLI

```bash
python cli.py
```

The system starts with a default admin account:

| Field    | Value       |
|----------|-------------|
| Username | `admin`     |
| Password | `Admin@123` |

### Run the Demo

```bash
python demo.py
```

This exercises every major feature — user registration, book management, borrowing, overdue simulation, analytics, notifications, fines, persistence, and the audit log.

### Bulk Import Books from CSV

```bash
# Generate a sample CSV to see the expected format
python -c "from book_import import generate_sample_csv; generate_sample_csv()"

# Import via the CLI: choose option [ Bulk Import Books (CSV)]
```

**Required CSV columns:** `isbn, title, author, publisher, year, genre, copies`  
**Optional columns:** `description, location`

---

##  Roles & Permissions

| Permission                          |   Admin    |    Staff   |    User    |
|-------------------------            |:----------:|:----------:|:----------:|
| Borrow / Return / Reserve           |  accepted  |  accepted  |  accepted  |
| Add / Update / Delete Books         |  accepted  |  accepted  |  declined  |
| View Inventory & Search             |  accepted  |  accepted  |  accepted  |
| Create Users                        |  accepted  |  accepted  |  declined  |
| Delete Users                        |  accepted  |  declined  |  declined  |
| Approve Registrations               |  accepted  |  accepted  |  declined  |
| Waive Fines                         |  accepted  |  declined  |  declined  |
| Collect Fines                       |  accepted  |  accepted  |  declined  |
| View Reports & Analytics            |  accepted  |  accepted  |  declined  |
| Full Dashboard & Exports            |  accepted  |  declined  |  declined  |
| View Audit Logs                     |  accepted  |  accepted  |  declined  |
| Save / Load Data                    |  accepted  |  declined  |  declined  |

---

##  Configuration

All tunable constants live in `config.py` and can be changed at runtime or persisted to `library_config.json`.

```python
from config import config, save_config

config.update(FINE_PER_DAY=10.0, BORROW_DURATION_DAYS=21)
save_config()   # persist for next run
```

Key settings:

| Setting                   | Default | Description                        |
|---------------------------|---------|------------------------------------|
| `BORROW_DURATION_DAYS`    | 14      | Standard loan period               |
| `MAX_BOOKS_USER`          | 3       | Concurrent borrow limit (user)     |
| `FINE_PER_DAY`            | 5.0     | Overdue fine in ₹ per day          |
| `FINE_GRACE_DAYS`         | 0       | Grace period before fines start    |
| `SESSION_TIMEOUT_MINUTES` | 60      | Auto-logout after inactivity       |
| `NOTIFY_DUE_REMINDER_DAYS`| 3       | Days before due to send reminder   |
| `PASSWORD_MIN_LENGTH`     | 8       | Minimum password length            |

---

##  Persistence

Library data is saved to `library_data.json` automatically on CLI exit, or manually:

```python
from persistence import save_library, load_library

save_library(lib, "library_data.json")
lib = load_library("library_data.json")
```

The JSON file stores users, books, borrow records, reservations, pending registrations, and the audit log.

---

##  Using as a Library (Programmatic API)

```python
from library import LibrarySystem
from models import Role

lib = LibrarySystem("My Library")

admin = lib.login("admin", "Admin@123")

# Create a staff account
staff = lib.create_user(admin, "alice", "Alice@123", Role.STAFF,
                        "Alice Smith", "alice@example.com", "9876543210")

# Add a book
book = lib.add_book(admin, "978-0-06-112008-4", "To Kill a Mockingbird",
                    "Harper Lee", "Lippincott", 1960, "Classic Fiction", 3)

# Borrow and return
user = lib.login("alice", "Alice@123")
record = lib.borrow_book(user, book.book_id)
lib.return_book(user, record.record_id)

# Analytics
lib.full_dashboard(admin)
```

---

##  Audit Trail

```python
from audit import AuditTrail

audit = AuditTrail(lib)

# Filter by category and date range
from datetime import date
entries = audit.filter(category="circulation", from_date=date(2025, 1, 1))
audit.print_entries(entries, title="Circulation Log")

# Export
audit.export_csv("reports/audit.csv")
audit.summary()
```

---

##  Tests

```bash
python test_suite.py
```

---

##  Roadmap

- [ ] Web interface (Flask / FastAPI)
- [ ] PostgreSQL / SQLite backend
- [ ] Real email integration (SMTP)
- [ ] Real SMS integration (Twilio)
- [ ] Book cover image support
- [ ] Barcode / QR code scanning
- [ ] Loan renewal / extension
- [ ] Inter-library loan tracking

---

##  License

MIT License. See [LICENSE](LICENSE) for details.
