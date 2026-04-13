"""
demo.py - Full demonstration of all Library Management System features
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, timedelta
from library import LibrarySystem
from models import Role
from persistence import save_library, load_library


def section(title: str):
    print(f"\n{'━'*65}")
    print(f"  🔷 {title}")
    print(f"{'━'*65}")


def demo():
    print(f"\n{'═'*65}")
    print("  📚  LIBRARY MANAGEMENT SYSTEM — FULL FEATURE DEMO")
    print(f"{'═'*65}")

    lib = LibrarySystem("Odisha State Central Library")

    section("1. Admin Login")
    admin = lib.login("admin", "Admin@123")

    section("2. Create Staff Account")
    lib.notifier.verbose = False
    staff = lib.create_user(admin, "staff_priya", "Staff@123", Role.STAFF,
                            "Priya Sharma", "priya@library.com", "9876543210")
    lib.notifier.verbose = True

    section("3. Users Self-Register")
    r1 = lib.register("reader_raj",    "User@123", "Raj Kumar",    "raj@mail.com",    "9123456780")
    r2 = lib.register("reader_ananya", "User@123", "Ananya Patel", "ananya@mail.com", "9000112233")
    r3 = lib.register("reader_ghost",  "User@123", "Ghost User",   "ghost@mail.com",  "9000000000")

    section("4. Admin Reviews Pending Registrations")
    lib.list_pending_registrations(admin)
    raj    = lib.approve_registration(admin, r1)
    ananya = lib.approve_registration(admin, r2)
    lib.reject_registration(admin, r3)

    raj    = lib.login("reader_raj",    "User@123")
    ananya = lib.login("reader_ananya", "User@123")

    section("5. Staff Adds Books to Catalogue")
    lib.notifier.verbose = False
    books_data = [
        ("978-001", "The Alchemist",              "Paulo Coelho",      "HarperOne",  1988, "Fiction",          5, "A philosophical novel.",          "A1"),
        ("978-002", "To Kill a Mockingbird",      "Harper Lee",        "Lippincott", 1960, "Classic Fiction",  3, "Pulitzer Prize winner.",          "A2"),
        ("978-003", "Introduction to Algorithms", "Thomas H. Cormen",  "MIT Press",  2009, "Computer Science", 4, "The definitive algorithms text.", "B1"),
        ("978-004", "Python Cookbook",            "David Beazley",     "O'Reilly",   2013, "Computer Science", 2, "Practical Python recipes.",       "B2"),
        ("978-005", "The God of Small Things",    "Arundhati Roy",     "Vintage",    1997, "Literary Fiction", 3, "Booker Prize 1997.",              "A3"),
        ("978-006", "The Kite Runner",            "Khaled Hosseini",   "Riverhead",  2003, "Fiction",          3, "A story of friendship.",          "A4"),
        ("978-007", "Sapiens",                    "Yuval Noah Harari", "Harper",     2011, "Non-Fiction",      4, "History of humankind.",           "C1"),
        ("978-008", "Atomic Habits",              "James Clear",       "Avery",      2018, "Self-Help",        5, "Build good habits.",              "C2"),
        ("978-009", "Deep Work",                  "Cal Newport",       "Grand C.",   2016, "Self-Help",        3, "Focus without distraction.",      "C3"),
        ("978-010", "The Stranger",               "Albert Camus",      "Vintage",    1942, "Fiction",          4, "Existentialist masterpiece.",     "A5"),
    ]
    book_objs = [lib.add_book(staff, *row) for row in books_data]
    lib.notifier.verbose = True
    print(f"  ✅ {len(book_objs)} books added.")

    section("6. Search & Inventory (visible to all roles)")
    lib.search_books(raj, genre="Fiction")
    lib.view_inventory(raj)

    section("7. Users Borrow Books")
    lib.notifier.verbose = False
    rec1 = lib.borrow_book(raj,    book_objs[0].book_id)   # Alchemist
    rec2 = lib.borrow_book(raj,    book_objs[5].book_id)   # Kite Runner
    rec3 = lib.borrow_book(ananya, book_objs[1].book_id)   # Mockingbird
    rec4 = lib.borrow_book(ananya, book_objs[6].book_id)   # Sapiens
    rec5 = lib.borrow_book(ananya, book_objs[7].book_id)   # Atomic Habits
    lib.notifier.verbose = True
    print("  ✅ Raj borrowed: The Alchemist, The Kite Runner")
    print("  ✅ Ananya borrowed: Mockingbird, Sapiens, Atomic Habits")

    section("8. Simulate Overdue & Due-Soon Borrows")
    rec2.due_date = date.today() - timedelta(days=7)    # Kite Runner 7d overdue
    rec3.due_date = date.today() - timedelta(days=3)    # Mockingbird 3d overdue
    rec1.due_date = date.today() + timedelta(days=2)    # Alchemist due in 2d
    print("  📛 Kite Runner (Raj)      : 7 days overdue")
    print("  📛 Mockingbird (Ananya)   : 3 days overdue")
    print("  ⏰ Alchemist (Raj)        : due in 2 days")

    section("9. Full Analytics Dashboard")
    lib.full_dashboard(admin)

    section("10. Send Overdue Alerts (Email + SMS)")
    lib.send_overdue_alerts(admin)

    section("11. Send Due-Soon Reminders")
    lib.send_due_soon_reminders(admin, within_days=3)

    section("12. Book Recommendations")
    print("  [Raj — Fiction reader]")
    lib.get_recommendations(raj, top_n=4)
    print("  [Ananya — Non-fiction & Self-Help reader]")
    lib.get_recommendations(ananya, top_n=4)

    section("13. Return Overdue Books → Fines")
    lib.return_book(raj, rec2.record_id)
    lib.return_book(ananya, rec3.record_id)
    print(f"\n  Raj's fine      : ₹{raj.fine_amount:.2f}")
    print(f"  Ananya's fine   : ₹{ananya.fine_amount:.2f}")

    section("14. Fine Collection & Waiver")
    lib.collect_fine(admin, raj.user_id, 20.0)
    lib.waive_fine(admin, raj.user_id)
    lib.collect_fine(admin, ananya.user_id, ananya.fine_amount)

    section("15. Staff Deletes a Book (new permission)")
    lib.return_book(ananya, rec4.record_id)   # return Sapiens first
    lib.delete_book(staff, book_objs[6].book_id)

    section("16. Notification Log")
    lib.view_notification_log(admin, last_n=25)

    section("17. Save Library State to JSON")
    save_library(lib, "demo_library.json")

    section("18. Reload & Verify Persistence")
    lib2 = load_library("demo_library.json")
    lib2.list_users(admin)

    section("19. System Audit Log")
    lib.view_logs(admin, last_n=30)

    print(f"\n{'═'*65}")
    print("  ✅ ALL FEATURES DEMONSTRATED SUCCESSFULLY!")
    print(f"{'═'*65}\n")


if __name__ == "__main__":
    demo()
