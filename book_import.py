"""
book_import.py - Bulk Book Import from CSV

CSV format (header row required):
    isbn,title,author,publisher,year,genre,copies,description,location

Columns description,location are optional and may be blank.

Usage:
    from book_import import import_books_csv, generate_sample_csv
    result = import_books_csv(lib, staff_user, "books.csv")
    print(result.summary())

Or from the CLI, choose menu option "📥 Bulk Import Books (CSV)".
"""

import csv
import os
from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from library import LibrarySystem
    from models import User

from validators import validate_book_fields
from exceptions import ValidationError


REQUIRED_COLUMNS = {"isbn", "title", "author", "publisher", "year", "genre", "copies"}
OPTIONAL_COLUMNS = {"description", "location"}
ALL_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS


@dataclass
class ImportResult:
    total_rows: int = 0
    imported: int = 0
    skipped_duplicate: int = 0
    failed: int = 0
    errors: List[dict] = field(default_factory=list)   # {row, field, reason}

    def summary(self) -> str:
        lines = [
            f"Import complete:",
            f"  Total rows      : {self.total_rows}",
            f"  Imported        : {self.imported}",
            f"  Skipped (dup.)  : {self.skipped_duplicate}",
            f"  Failed          : {self.failed}",
        ]
        if self.errors:
            lines.append("\n  Errors:")
            for e in self.errors[:20]:   # show at most 20
                lines.append(f"    Row {e['row']}: [{e['field']}] {e['reason']}")
            if len(self.errors) > 20:
                lines.append(f"    … and {len(self.errors) - 20} more error(s)")
        return "\n".join(lines)

    def print_summary(self):
        icon = "✅" if self.failed == 0 else "⚠️"
        print(f"\n{icon} {self.summary()}\n")


def import_books_csv(lib: "LibrarySystem", actor: "User",
                     filepath: str,
                     skip_duplicates: bool = True) -> ImportResult:
    """
    Read a CSV file and add books to the library.

    - Rows with validation errors are skipped (error logged in result).
    - Duplicate ISBNs: if skip_duplicates=True the row is counted as
      skipped; otherwise copies are merged into the existing record
      (same behaviour as add_book).
    - Requires actor to have 'add_book' permission.
    """
    from auth import has_permission
    from exceptions import PermissionDeniedError

    if not has_permission(actor, "add_book"):
        raise PermissionDeniedError(actor.role.value, "add_book")

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CSV file not found: '{filepath}'")

    result = ImportResult()

    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        # Validate header
        if reader.fieldnames is None:
            raise ValueError("CSV file is empty or has no header row.")
        cols = {c.strip().lower() for c in reader.fieldnames}
        missing = REQUIRED_COLUMNS - cols
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")

        for row_num, raw in enumerate(reader, start=2):
            row = {k.strip().lower(): v.strip() for k, v in raw.items()}
            result.total_rows += 1

            # Validate fields
            try:
                validated = validate_book_fields(
                    isbn=row.get("isbn", ""),
                    title=row.get("title", ""),
                    author=row.get("author", ""),
                    year=row.get("year", ""),
                    copies=row.get("copies", ""),
                    genre=row.get("genre", ""),
                )
            except (ValidationError, Exception) as e:
                result.failed += 1
                result.errors.append({
                    "row": row_num,
                    "field": getattr(e, "message", str(e)).split("'")[1] if "'" in str(e) else "?",
                    "reason": str(e),
                })
                continue

            # Duplicate check
            isbn_exists = any(b.isbn == validated["isbn"] for b in lib._books.values())
            if isbn_exists and skip_duplicates:
                result.skipped_duplicate += 1
                continue

            # Suppress per-book print during bulk import
            import io, sys
            _stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                lib.add_book(
                    actor,
                    isbn=validated["isbn"],
                    title=validated["title"],
                    author=validated["author"],
                    publisher=row.get("publisher", "Unknown"),
                    year=validated["year"],
                    genre=validated["genre"],
                    copies=validated["copies"],
                    description=row.get("description", ""),
                    location=row.get("location", ""),
                )
                result.imported += 1
            except Exception as e:
                result.failed += 1
                result.errors.append({"row": row_num, "field": "add_book", "reason": str(e)})
            finally:
                sys.stdout = _stdout

    result.print_summary()
    lib._log(actor.username, "BULK_IMPORT",
             f"CSV import '{filepath}': {result.imported} added, {result.failed} failed")
    return result


def generate_sample_csv(filepath: str = "sample_books.csv"):
    """Write a sample CSV file showing the expected format."""
    rows = [
        ["isbn",         "title",                     "author",           "publisher",    "year","genre",           "copies","description",                   "location"],
        ["978-0-06-112008-4","To Kill a Mockingbird","Harper Lee",        "Lippincott",   "1960","Classic Fiction",  "3",    "Pulitzer Prize winner.",         "Shelf A1"],
        ["978-0-7432-7356-5","The Alchemist",         "Paulo Coelho",     "HarperOne",    "1988","Fiction",          "5",    "A novel about following dreams.", "Shelf A2"],
        ["978-0-14-028329-7","The God of Small Things","Arundhati Roy",   "Random House", "1997","Literary Fiction", "2",    "Booker Prize 1997.",             "Shelf A3"],
        ["978-0-385-33348-1","The Kite Runner",        "Khaled Hosseini", "Riverhead",    "2003","Fiction",          "4",    "A story of friendship.",         "Shelf A4"],
        ["978-0-7432-7357-2","Introduction to Algorithms","Thomas H. Cormen","MIT Press", "2009","Computer Science", "3",    "Definitive algorithms text.",    "Shelf B1"],
        ["978-1-4493-5501-0","Python Cookbook",        "David Beazley",   "O'Reilly",     "2013","Computer Science", "2",    "Practical Python recipes.",      "Shelf B2"],
        ["978-0-679-72020-1","The Stranger",           "Albert Camus",    "Vintage",      "1942","Fiction",          "4",    "Existentialist masterpiece.",    "Shelf A5"],
        ["978-0-7432-7000-7","Sapiens",                "Yuval Noah Harari","Harper",      "2011","Non-Fiction",      "4",    "History of humankind.",          "Shelf C1"],
        ["978-1-250-30185-1","Atomic Habits",          "James Clear",     "Avery",        "2018","Self-Help",        "5",    "Build good habits.",             "Shelf C2"],
        ["978-0-525-55360-5","Deep Work",              "Cal Newport",     "Grand Central","2016","Self-Help",        "3",    "Focus without distraction.",     "Shelf C3"],
    ]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"📄 Sample CSV written to '{filepath}' ({len(rows)-1} books)")
    return filepath
