"""
cli.py - Interactive Command-Line Interface for Library Management System
"""

from library import LibrarySystem
from models import Role
from auth import has_permission


def separator(char="─", width=60):
    print(char * width)


def print_header(title: str):
    separator("═")
    print(f"  {title}")
    separator("═")


def menu_prompt(options: list) -> str:
    print()
    for key, label in options:
        print(f"  [{key}] {label}")
    print()
    return input("  Enter choice: ").strip().lower()


def do_login(lib: LibrarySystem):
    """Prompt login/register until successful or quit. Returns User or None."""
    while True:
        print("\n  [L] Login    [R] Register    [Q] Quit")
        choice = input("  Enter choice: ").strip().lower()
        if choice == "q":
            return None
        if choice == "r":
            print("\n  ── Self Registration ──")
            uname     = input("  Username  : ").strip()
            pw        = input("  Password  : ").strip()
            full_name = input("  Full Name : ").strip()
            email     = input("  Email     : ").strip()
            phone     = input("  Phone     : ").strip()
            try:
                lib.register(uname, pw, full_name, email, phone)
            except ValueError as e:
                print(f"  ❌ {e}")
        elif choice == "l":
            username = input("  Username: ").strip()
            password = input("  Password: ").strip()
            user = lib.login(username, password)
            if user:
                return user


def run_cli():
    # ── Startup: try to load saved data ───────────────────────────────────────
    import os
    SAVE_FILE = "library_data.json"
    try:
        if os.path.exists(SAVE_FILE):
            from persistence import load_library
            lib = load_library(SAVE_FILE)
        else:
            lib = LibrarySystem("City Public Library")
    except Exception as e:
        print(f"  ⚠️  Could not load saved data: {e}. Starting fresh.")
        lib = LibrarySystem("City Public Library")

    print_header("📚 LIBRARY MANAGEMENT SYSTEM")
    print("  Default admin: username=admin  password=Admin@123")
    separator()

    current_user = do_login(lib)
    if current_user is None:
        print("  Goodbye! 👋")
        return

    # ── Main Menu ─────────────────────────────────────────────────────────────
    while True:
        role = current_user.role
        print(f"\n  Logged in as: {current_user.full_name} [{role.value.upper()}]")
        separator()

        options = [
            ("1",  "📚 Search Books"),
            ("2",  "📦 View Inventory"),
            ("6",  "📖 Borrow Book"),
            ("7",  "🔄 Return Book"),
            ("8",  "🔒 Reserve Book"),
            ("9",  "📋 My History"),
            ("rec","✨ Book Recommendations"),
        ]

        if has_permission(current_user, "add_book"):
            options.insert(2, ("3", "➕ Add Book"))
        if has_permission(current_user, "delete_book"):
            options.insert(3, ("4", "🗑️  Delete Book"))
        if has_permission(current_user, "update_book"):
            options.insert(4, ("5", "✏️  Update Book"))

        if has_permission(current_user, "view_borrow_history"):
            options.append(("10", "📋 All Borrow History"))
        if has_permission(current_user, "view_all_users"):
            options.append(("11", "👥 List Users"))
        if has_permission(current_user, "create_user"):
            options.append(("12", "👤 Create User"))
            options.append(("18", "📥 Pending Registrations"))
            options.append(("19", "✅ Approve Registration"))
            options.append(("20", "❌ Reject Registration"))
        if has_permission(current_user, "delete_user"):
            options.append(("13", "🗑️  Delete User"))
        if has_permission(current_user, "waive_fine"):
            options.append(("14", "💸 Waive Fine"))
        if has_permission(current_user, "collect_fine"):
            options.append(("15", "💰 Collect Fine"))

        # Analytics & Alerts
        if has_permission(current_user, "view_reports"):
            options.append(("a1", "📛 Overdue Report"))
            options.append(("a2", "⏰ Due Soon Report"))
            options.append(("a3", "🔔 Send Overdue Alerts"))
            options.append(("a4", "⏰ Send Due-Soon Reminders"))
            options.append(("a5", "📣 Notification Log"))
        if has_permission(current_user, "generate_reports"):
            options.append(("a6", "📊 Full Analytics Dashboard"))

        if has_permission(current_user, "view_logs"):
            options.append(("17", "🗒️  System Logs"))

        # Persistence
        if has_permission(current_user, "backup_data"):
            options.append(("sv", "💾 Save Library Data"))
            options.append(("ld", "📂 Load Library Data"))

        options.append(("x",  "🚪 Logout"))
        options.append(("q",  "❌ Quit"))

        choice = menu_prompt(options)

        try:
            if choice == "1":
                q = input("  Search (title/author/isbn, blank=all): ").strip()
                avail = input("  Available only? (y/n): ").strip().lower() == "y"
                lib.search_books(current_user, query=q, available_only=avail)

            elif choice == "2":
                lib.view_inventory(current_user)

            elif choice == "3":
                print("\n  ── Add New Book ──")
                isbn      = input("  ISBN        : ").strip()
                title     = input("  Title       : ").strip()
                author    = input("  Author      : ").strip()
                publisher = input("  Publisher   : ").strip()
                year      = int(input("  Year        : ").strip())
                genre     = input("  Genre       : ").strip()
                copies    = int(input("  Copies      : ").strip())
                desc      = input("  Description : ").strip()
                loc       = input("  Shelf Loc   : ").strip()
                lib.add_book(current_user, isbn, title, author, publisher,
                             year, genre, copies, desc, loc)

            elif choice == "4":
                book_id = input("  Book ID to delete: ").strip()
                lib.delete_book(current_user, book_id)

            elif choice == "5":
                book_id = input("  Book ID to update: ").strip()
                print("  Leave blank to skip a field.")
                updates = {}
                for field in ["title", "author", "publisher", "genre", "description", "location"]:
                    val = input(f"  {field.capitalize():<12}: ").strip()
                    if val:
                        updates[field] = val
                year = input("  Year        : ").strip()
                if year:
                    updates["year"] = int(year)
                if updates:
                    lib.update_book(current_user, book_id, **updates)
                else:
                    print("  No changes made.")

            elif choice == "6":
                book_id     = input("  Book ID to borrow: ").strip()
                borrower_id = None
                if has_permission(current_user, "process_return"):
                    on_behalf = input("  Borrow on behalf of user? (user_id or blank): ").strip()
                    if on_behalf:
                        borrower_id = on_behalf
                lib.borrow_book(current_user, book_id, borrower_id)

            elif choice == "7":
                record_id = input("  Record ID to return: ").strip()
                lib.return_book(current_user, record_id)

            elif choice == "8":
                book_id = input("  Book ID to reserve: ").strip()
                lib.reserve_book(current_user, book_id)

            elif choice == "9":
                lib.view_my_history(current_user)

            elif choice == "rec":
                n = int(input("  How many recommendations? (default 5): ").strip() or "5")
                lib.get_recommendations(current_user, n)

            elif choice == "10":
                active = input("  Active borrows only? (y/n): ").strip().lower() == "y"
                lib.view_all_borrow_history(current_user, active_only=active)

            elif choice == "11":
                role_filter_str = input("  Filter by role (admin/staff/user/blank=all): ").strip().lower()
                role_filter = None
                if role_filter_str in ("admin", "staff", "user"):
                    role_filter = Role(role_filter_str)
                lib.list_users(current_user, role_filter)

            elif choice == "12":
                print("\n  ── Create New User ──")
                uname     = input("  Username  : ").strip()
                pw        = input("  Password  : ").strip()
                role_str  = input("  Role (admin/staff/user): ").strip().lower()
                full_name = input("  Full Name : ").strip()
                email     = input("  Email     : ").strip()
                phone     = input("  Phone     : ").strip()
                try:
                    r = Role(role_str)
                    lib.create_user(current_user, uname, pw, r, full_name, email, phone)
                except ValueError:
                    print(f"  ❌ Invalid role '{role_str}'")

            elif choice == "13":
                uid = input("  User ID to delete: ").strip()
                lib.delete_user(current_user, uid)

            elif choice == "14":
                uid = input("  User ID to waive fine: ").strip()
                lib.waive_fine(current_user, uid)

            elif choice == "15":
                uid = input("  User ID: ").strip()
                amt = float(input("  Amount to collect (₹): ").strip())
                lib.collect_fine(current_user, uid, amt)

            elif choice == "17":
                n = int(input("  Last N logs (default 20): ").strip() or "20")
                lib.view_logs(current_user, n)

            elif choice == "18":
                lib.list_pending_registrations(current_user)

            elif choice == "19":
                lib.list_pending_registrations(current_user)
                reg_id = input("  Registration ID to approve: ").strip()
                lib.approve_registration(current_user, reg_id)

            elif choice == "20":
                lib.list_pending_registrations(current_user)
                reg_id = input("  Registration ID to reject: ").strip()
                lib.reject_registration(current_user, reg_id)

            elif choice == "a1":
                lib.view_overdue_report(current_user)

            elif choice == "a2":
                d = int(input("  Due within how many days? (default 3): ").strip() or "3")
                lib.view_due_soon(current_user, d)

            elif choice == "a3":
                lib.send_overdue_alerts(current_user)

            elif choice == "a4":
                d = int(input("  Remind if due within how many days? (default 3): ").strip() or "3")
                lib.send_due_soon_reminders(current_user, d)

            elif choice == "a5":
                n = int(input("  Last N notifications (default 20): ").strip() or "20")
                lib.view_notification_log(current_user, n)

            elif choice == "a6":
                lib.full_dashboard(current_user)

            elif choice == "sv":
                fname = input(f"  Save filename (default '{SAVE_FILE}'): ").strip() or SAVE_FILE
                from persistence import save_library
                save_library(lib, fname)

            elif choice == "ld":
                fname = input(f"  Load filename (default '{SAVE_FILE}'): ").strip() or SAVE_FILE
                try:
                    from persistence import load_library
                    lib = load_library(fname)
                    current_user = lib._users.get(current_user.user_id) or current_user
                except FileNotFoundError as e:
                    print(f"  ❌ {e}")

            elif choice == "x":
                print(f"\n  👋 Logged out: {current_user.full_name}")
                current_user = do_login(lib)
                if current_user is None:
                    print("  Goodbye! 👋")
                    return

            elif choice == "q":
                # Auto-save on quit
                try:
                    from persistence import save_library
                    save_library(lib, SAVE_FILE)
                except Exception as e:
                    print(f"  ⚠️  Auto-save failed: {e}")
                print("\n  Goodbye! 👋")
                break

            else:
                print("  ⚠️  Invalid option.")

        except PermissionError as e:
            print(f"\n  {e}")
        except ValueError as e:
            print(f"\n  ❌ Error: {e}")
        except Exception as e:
            print(f"\n  ⚠️  Unexpected error: {e}")


if __name__ == "__main__":
    run_cli()
