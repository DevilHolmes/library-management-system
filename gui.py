import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import date, timedelta
from typing import Optional

# ----------------- Bootstrap path -------------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from library import LibrarySystem
from models import Role, BookStatus
from auth import has_permission
from persistence import save_library, load_library

SAVE_FILE = "library_data.json"

# -----------Palette & fonts ---------------------------------------------------------------------------------
CLR = {
    "bg":        "#0f1117",
    "surface":   "#1a1d27",
    "card":      "#22263a",
    "border":    "#2e3350",
    "accent":    "#5c7cfa",
    "accent2":   "#48dbaf",
    "danger":    "#ff6b6b",
    "warn":      "#ffd166",
    "text":      "#e8eaf0",
    "muted":     "#8890a8",
    "entry_bg":  "#1e2235",
    "sel":       "#2d3555",
    "header_bg": "#141829",
}

FONT_TITLE  = ("Segoe UI", 22, "bold")
FONT_SECT   = ("Segoe UI", 13, "bold")
FONT_BODY   = ("Segoe UI", 10)
FONT_SMALL  = ("Segoe UI", 9)
FONT_MONO   = ("Consolas", 9)
FONT_BTN    = ("Segoe UI", 10, "bold")


# ---------- Helpers -------------------------------------------------------------------------------------

def styled_btn(parent, text, command, color=None, width=18, **kw):
    bg = color or CLR["accent"]
    hover = _darken(bg)
    btn = tk.Button(parent, text=text, command=command,
                    bg=bg, fg=CLR["text"], relief="flat",
                    font=FONT_BTN, cursor="hand2",
                    activebackground=hover, activeforeground=CLR["text"],
                    bd=0, padx=12, pady=6, width=width, **kw)
    btn.bind("<Enter>", lambda e: btn.config(bg=hover))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    return btn


def _darken(hex_color: str) -> str:
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    r, g, b = max(0, r - 30), max(0, g - 30), max(0, b - 30)
    return f"#{r:02x}{g:02x}{b:02x}"


def lbl(parent, text, font=FONT_BODY, fg=None, **kw):
    return tk.Label(parent, text=text, bg=CLR["bg"], fg=fg or CLR["text"],
                    font=font, **kw)


def card_frame(parent, **kw):
    return tk.Frame(parent, bg=CLR["card"], bd=0, **kw)


def entry_field(parent, textvariable=None, show=None, width=30):
    e = tk.Entry(parent, bg=CLR["entry_bg"], fg=CLR["text"],
                 insertbackground=CLR["text"], relief="flat",
                 font=FONT_BODY, bd=4,
                 textvariable=textvariable, show=show, width=width)
    return e


def scrolled_tree(parent, columns, headings, col_widths=None, height=14, **kw):
    frame = tk.Frame(parent, bg=CLR["bg"])
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Dark.Treeview",
                     background=CLR["card"],
                     foreground=CLR["text"],
                     rowheight=24,
                     fieldbackground=CLR["card"],
                     bordercolor=CLR["border"],
                     font=FONT_SMALL)
    style.configure("Dark.Treeview.Heading",
                     background=CLR["header_bg"],
                     foreground=CLR["accent"],
                     font=("Segoe UI", 9, "bold"),
                     relief="flat")
    style.map("Dark.Treeview",
              background=[("selected", CLR["sel"])],
              foreground=[("selected", CLR["text"])])

    tv = ttk.Treeview(frame, columns=columns, show="headings",
                       style="Dark.Treeview", height=height, **kw)
    for i, col in enumerate(columns):
        tv.heading(col, text=headings[i])
        w = col_widths[i] if col_widths else 120
        tv.column(col, width=w, minwidth=40, anchor="w")

    vsb = ttk.Scrollbar(frame, orient="vertical", command=tv.yview)
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=tv.xview)
    tv.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tv.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    return frame, tv


def section_label(parent, text):
    f = tk.Frame(parent, bg=CLR["bg"])
    tk.Label(f, text=text, bg=CLR["bg"], fg=CLR["accent"],
             font=FONT_SECT).pack(side="left")
    tk.Frame(f, bg=CLR["border"], height=1).pack(side="left", fill="x",
                                                   expand=True, padx=(10, 0))
    return f


#  ===========================LOGIN WINDOW================================================================================

class LoginWindow(tk.Toplevel):
    def __init__(self, master, lib: LibrarySystem, callback):
        super().__init__(master)
        self.lib = lib
        self.callback = callback
        self.title("Library — Sign In")
        self.configure(bg=CLR["bg"])
        self.resizable(False, False)
        self._build()
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._center)

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")

    def _on_close(self):
        self.master.destroy()

    def _build(self):
        pad = {"padx": 40, "pady": 8}

        # Header
        hdr = tk.Frame(self, bg=CLR["surface"], padx=40, pady=24)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📚", bg=CLR["surface"], fg=CLR["accent"],
                 font=("Segoe UI", 36)).pack()
        tk.Label(hdr, text="Library Management System",
                 bg=CLR["surface"], fg=CLR["text"], font=FONT_TITLE).pack()
        tk.Label(hdr, text="Sign in to continue",
                 bg=CLR["surface"], fg=CLR["muted"], font=FONT_SMALL).pack(pady=(4, 0))

        body = tk.Frame(self, bg=CLR["bg"], padx=40, pady=30)
        body.pack(fill="both")

        # Tabs: Login / Register
        self._tab = tk.StringVar(value="login")
        tab_bar = tk.Frame(body, bg=CLR["bg"])
        tab_bar.pack(fill="x", pady=(0, 16))
        for val, txt in [("login", "Login"), ("register", "Register")]:
            tk.Radiobutton(tab_bar, text=txt, variable=self._tab, value=val,
                           command=self._switch_tab,
                           bg=CLR["bg"], fg=CLR["text"], selectcolor=CLR["bg"],
                           activebackground=CLR["bg"], activeforeground=CLR["accent"],
                           font=FONT_BTN, indicatoron=False,
                           relief="flat", bd=0,
                           padx=16, pady=6, cursor="hand2").pack(side="left", padx=4)

        self._login_frame  = self._build_login(body)
        self._reg_frame    = self._build_register(body)
        self._login_frame.pack(fill="x")

        self._status = tk.Label(body, text="", bg=CLR["bg"],
                                 fg=CLR["danger"], font=FONT_SMALL, wraplength=300)
        self._status.pack(pady=4)

    def _build_login(self, parent):
        f = tk.Frame(parent, bg=CLR["bg"])
        fields = [("Username", False), ("Password", True)]
        self._login_vars = {}
        for label, secret in fields:
            tk.Label(f, text=label, bg=CLR["bg"], fg=CLR["muted"],
                     font=FONT_SMALL).pack(anchor="w")
            var = tk.StringVar()
            self._login_vars[label] = var
            e = entry_field(f, textvariable=var, show="•" if secret else None, width=34)
            e.pack(fill="x", pady=(2, 10))
        e.bind("<Return>", lambda _: self._do_login())
        styled_btn(f, "Sign In", self._do_login, width=34).pack(fill="x", pady=4)
        tk.Label(f, text="Default admin: admin / Admin@123",
                 bg=CLR["bg"], fg=CLR["muted"], font=FONT_SMALL).pack(pady=2)
        return f

    def _build_register(self, parent):
        f = tk.Frame(parent, bg=CLR["bg"])
        self._reg_vars = {}
        fields = [
            ("Username", False), ("Password", True),
            ("Full Name", False), ("Email", False), ("Phone", False),
        ]
        for label, secret in fields:
            tk.Label(f, text=label, bg=CLR["bg"], fg=CLR["muted"],
                     font=FONT_SMALL).pack(anchor="w")
            var = tk.StringVar()
            self._reg_vars[label] = var
            entry_field(f, textvariable=var, show="•" if secret else None,
                        width=34).pack(fill="x", pady=(2, 8))
        styled_btn(f, "Submit Registration", self._do_register,
                   color=CLR["accent2"], width=34).pack(fill="x", pady=4)
        return f

    def _switch_tab(self):
        if self._tab.get() == "login":
            self._reg_frame.pack_forget()
            self._login_frame.pack(fill="x")
        else:
            self._login_frame.pack_forget()
            self._reg_frame.pack(fill="x")
        self._status.config(text="")

    def _do_login(self):
        uname = self._login_vars["Username"].get().strip()
        pwd   = self._login_vars["Password"].get()
        if not uname or not pwd:
            self._status.config(text="Enter username and password.")
            return
        import io
        buf = io.StringIO()
        sys.stdout = buf
        user = self.lib.login(uname, pwd)
        sys.stdout = sys.__stdout__
        if user:
            self.destroy()
            self.callback(user)
        else:
            self._status.config(text="Invalid credentials. Please try again.")

    def _do_register(self):
        v = self._reg_vars
        try:
            reg_id = self.lib.register(
                v["Username"].get().strip(),
                v["Password"].get(),
                v["Full Name"].get().strip(),
                v["Email"].get().strip(),
                v["Phone"].get().strip(),
            )
            self._status.config(fg=CLR["accent2"],
                text=f"Request submitted (ID: {reg_id}). Await admin approval.")
        except Exception as e:
            self._status.config(fg=CLR["danger"], text=str(e))


# --------------------------------  MAIN APPLICATION---------------------------------------------------------

class LibraryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📚 Library Management System")
        self.configure(bg=CLR["bg"])
        self.geometry("1200x780")
        self.minsize(900, 600)

        # Load or create library
        try:
            if os.path.exists(SAVE_FILE):
                self.lib = load_library(SAVE_FILE)
            else:
                self.lib = LibrarySystem("City Public Library")
        except Exception:
            self.lib = LibrarySystem("City Public Library")

        self.current_user = None
        self._build_shell()
        self.after(200, self._show_login)

    # ----------- Shell (sidebar + content area) ----------------------------------------------------

    def _build_shell(self):
        self._sidebar = tk.Frame(self, bg=CLR["surface"], width=210)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        self._content = tk.Frame(self, bg=CLR["bg"])
        self._content.pack(side="left", fill="both", expand=True)

        self._build_sidebar()

    def _build_sidebar(self):
        sb = self._sidebar
        # Logo
        logo = tk.Frame(sb, bg=CLR["surface"], pady=20)
        logo.pack(fill="x")
        tk.Label(logo, text="📚", bg=CLR["surface"],
                 fg=CLR["accent"], font=("Segoe UI", 28)).pack()
        tk.Label(logo, text="Library", bg=CLR["surface"],
                 fg=CLR["text"], font=("Segoe UI", 13, "bold")).pack()
        self._lib_name_lbl = tk.Label(logo, text=self.lib.library_name,
                                       bg=CLR["surface"], fg=CLR["muted"],
                                       font=FONT_SMALL, wraplength=160)
        self._lib_name_lbl.pack()

        tk.Frame(sb, bg=CLR["border"], height=1).pack(fill="x", padx=16, pady=4)

        self._user_lbl = tk.Label(sb, text="Not logged in",
                                   bg=CLR["surface"], fg=CLR["muted"],
                                   font=FONT_SMALL, wraplength=160)
        self._user_lbl.pack(pady=(4, 8))

        # Nav buttons container
        self._nav_frame = tk.Frame(sb, bg=CLR["surface"])
        self._nav_frame.pack(fill="both", expand=True)

        # Bottom buttons
        bot = tk.Frame(sb, bg=CLR["surface"], pady=12)
        bot.pack(fill="x", side="bottom")
        styled_btn(bot, "💾  Save", self._save, width=20,
                   color=CLR["card"]).pack(padx=12, pady=2, fill="x")
        styled_btn(bot, "🔓  Logout", self._logout, width=20,
                   color=CLR["card"]).pack(padx=12, pady=2, fill="x")

    def _rebuild_nav(self):
        for w in self._nav_frame.winfo_children():
            w.destroy()

        u = self.current_user
        nav_items = []

        # Everyone
        nav_items += [
            ("🔍  Search Books",    self._page_search),
            ("📦  Inventory",       self._page_inventory),
            ("📖  Borrow Book",     self._page_borrow),
            ("🔄  Return Book",     self._page_return),
            ("🔒  Reserve Book",    self._page_reserve),
            ("📋  My History",      self._page_my_history),
            ("✨  Recommendations", self._page_recommendations),
        ]
        # Staff / Admin
        if has_permission(u, "add_book"):
            nav_items.append(("➕  Add Book",          self._page_add_book))
        if has_permission(u, "delete_book"):
            nav_items.append(("🗑️  Delete Book",        self._page_delete_book))
        if has_permission(u, "update_book"):
            nav_items.append(("✏️  Edit Book",          self._page_edit_book))
        if has_permission(u, "view_borrow_history"):
            nav_items.append(("📋  All Borrows",        self._page_all_history))
        if has_permission(u, "view_all_users"):
            nav_items.append(("👥  Users",              self._page_users))
        if has_permission(u, "create_user"):
            nav_items.append(("👤  Create User",        self._page_create_user))
            nav_items.append(("📥  Registrations",      self._page_registrations))
        if has_permission(u, "waive_fine") or has_permission(u, "collect_fine"):
            nav_items.append(("💰  Fines",              self._page_fines))
        if has_permission(u, "view_reports"):
            nav_items.append(("📛  Overdue Report",     self._page_overdue))
            nav_items.append(("🔔  Send Alerts",        self._do_send_alerts))
        if has_permission(u, "generate_reports"):
            nav_items.append(("📊  Dashboard",          self._page_dashboard))
        if has_permission(u, "view_logs"):
            nav_items.append(("🗒️  Audit Log",          self._page_logs))

        for label, cmd in nav_items:
            self._nav_btn(label, cmd)

    def _nav_btn(self, text, command):
        btn = tk.Button(self._nav_frame, text=text, command=command,
                        bg=CLR["surface"], fg=CLR["text"], relief="flat",
                        font=FONT_SMALL, anchor="w", padx=16, pady=8,
                        cursor="hand2", activebackground=CLR["card"],
                        activeforeground=CLR["accent"])
        btn.pack(fill="x")
        btn.bind("<Enter>", lambda e: btn.config(bg=CLR["card"]))
        btn.bind("<Leave>", lambda e: btn.config(bg=CLR["surface"]))

    # --------------- Content area helpers ---------------------------------------------------------

    def _clear_content(self):
        for w in self._content.winfo_children():
            w.destroy()

    def _page_header(self, title, subtitle=""):
        hdr = tk.Frame(self._content, bg=CLR["header_bg"], padx=24, pady=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text=title, bg=CLR["header_bg"], fg=CLR["text"],
                 font=FONT_SECT).pack(anchor="w")
        if subtitle:
            tk.Label(hdr, text=subtitle, bg=CLR["header_bg"], fg=CLR["muted"],
                     font=FONT_SMALL).pack(anchor="w")
        return hdr

    def _status_bar(self, parent):
        bar = tk.Label(parent, text="", bg=CLR["surface"], fg=CLR["accent2"],
                       font=FONT_SMALL, anchor="w", padx=10)
        bar.pack(fill="x", side="bottom")
        return bar

    # ── Login / Logout ────────────────────────────────────────────────────────

    def _show_login(self):
        self.withdraw()
        LoginWindow(self, self.lib, self._on_login)

    def _on_login(self, user):
        self.current_user = user
        self._user_lbl.config(
            text=f"{user.full_name}\n[{user.role.value.upper()}]",
            fg=CLR["accent2"])
        self._rebuild_nav()
        self.deiconify()
        self._page_search()

    def _logout(self):
        if messagebox.askyesno("Logout", "Save and logout?"):
            self._save()
        self.current_user = None
        self.withdraw()
        self._show_login()

    def _save(self):
        try:
            save_library(self.lib, SAVE_FILE)
            messagebox.showinfo("Saved", f"Library data saved to '{SAVE_FILE}'.")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    #==============================================================================================
    #  PAGES
    # ==============================================================================================

    # ----------------- Search Books ----------------------------------------------------------------

    def _page_search(self):
        self._clear_content()
        self._page_header("🔍 Search Books", "Search by title, author, ISBN, or genre")

        top = tk.Frame(self._content, bg=CLR["bg"], padx=16, pady=12)
        top.pack(fill="x")

        sv = tk.StringVar()
        genre_v = tk.StringVar()
        avail_v = tk.BooleanVar()

        tk.Label(top, text="Search:", bg=CLR["bg"], fg=CLR["muted"],
                 font=FONT_SMALL).grid(row=0, column=0, padx=4, sticky="w")
        entry_field(top, textvariable=sv, width=28).grid(row=0, column=1, padx=4)
        tk.Label(top, text="Genre:", bg=CLR["bg"], fg=CLR["muted"],
                 font=FONT_SMALL).grid(row=0, column=2, padx=4, sticky="w")
        entry_field(top, textvariable=genre_v, width=16).grid(row=0, column=3, padx=4)
        tk.Checkbutton(top, text="Available only", variable=avail_v,
                       bg=CLR["bg"], fg=CLR["text"], selectcolor=CLR["bg"],
                       activebackground=CLR["bg"], font=FONT_SMALL).grid(
            row=0, column=4, padx=8)

        cols   = ["ID", "Title", "Author", "Genre", "Year", "Available", "Status", "Location"]
        widths = [100,  220,     160,      120,     55,     80,          80,       90]
        fr, tv = scrolled_tree(self._content, cols, cols, widths, height=18)
        fr.pack(fill="both", expand=True, padx=16, pady=8)
        status = self._status_bar(self._content)

        def do_search(*_):
            for row in tv.get_children():
                tv.delete(row)
            import io
            sys.stdout = io.StringIO()
            results = self.lib.search_books(
                self.current_user,
                query=sv.get().strip(),
                genre=genre_v.get().strip(),
                available_only=avail_v.get())
            sys.stdout = sys.__stdout__
            for b in results:
                tag = "ok" if b.available_copies > 0 else "na"
                tv.insert("", "end", values=(
                    b.book_id, b.title, b.author, b.genre, b.year,
                    f"{b.available_copies}/{b.total_copies}",
                    b.status.value, b.location), tags=(tag,))
            tv.tag_configure("ok", foreground=CLR["accent2"])
            tv.tag_configure("na", foreground=CLR["muted"])
            status.config(text=f"  {len(results)} result(s) found")

        sv.trace_add("write", do_search)
        genre_v.trace_add("write", do_search)
        avail_v.trace_add("write", do_search)

        styled_btn(top, "🔍 Search", do_search, width=12).grid(row=0, column=5, padx=8)
        do_search()

    # --------- Inventory --------------------------------------------------------------------------------

    def _page_inventory(self):
        self._clear_content()
        self._page_header("📦 Inventory", f"— {self.lib.library_name}")

        books = list(self.lib._books.values())
        total_copies   = sum(b.total_copies   for b in books)
        avail_copies   = sum(b.available_copies for b in books)

        stat = tk.Frame(self._content, bg=CLR["card"], padx=20, pady=14)
        stat.pack(fill="x", padx=16, pady=(12, 0))
        for label, val, col in [
            ("Titles",    len(books),                    CLR["text"]),
            ("Copies",    total_copies,                  CLR["text"]),
            ("Available", avail_copies,                  CLR["accent2"]),
            ("Borrowed",  total_copies - avail_copies,   CLR["warn"]),
        ]:
            f = tk.Frame(stat, bg=CLR["card"])
            f.pack(side="left", padx=24)
            tk.Label(f, text=str(val), bg=CLR["card"], fg=col,
                     font=("Segoe UI", 20, "bold")).pack()
            tk.Label(f, text=label, bg=CLR["card"], fg=CLR["muted"],
                     font=FONT_SMALL).pack()

        cols   = ["ID", "ISBN", "Title", "Author", "Publisher", "Year", "Genre",
                  "Avail/Total", "Location"]
        widths = [95,   110,    210,     160,      120,         55,     110,
                  80,          90]
        fr, tv = scrolled_tree(self._content, cols, cols, widths, height=14)
        fr.pack(fill="both", expand=True, padx=16, pady=12)

        for b in sorted(books, key=lambda x: x.title):
            avail_str = f"{b.available_copies}/{b.total_copies}"
            tag = "ok" if b.available_copies > 0 else "na"
            tv.insert("", "end", values=(
                b.book_id, b.isbn, b.title, b.author, b.publisher,
                b.year, b.genre, avail_str, b.location), tags=(tag,))
        tv.tag_configure("ok", foreground=CLR["text"])
        tv.tag_configure("na", foreground=CLR["muted"])

    # ------- Add Book -----------------------------------------------------

    def _page_add_book(self):
        self._clear_content()
        self._page_header("➕ Add New Book", "Fill in book details")

        body = tk.Frame(self._content, bg=CLR["bg"], padx=36, pady=24)
        body.pack(fill="both", expand=True)

        fields = [
            ("ISBN *",       "isbn"),
            ("Title *",      "title"),
            ("Author *",     "author"),
            ("Publisher",    "publisher"),
            ("Year *",       "year"),
            ("Genre *",      "genre"),
            ("Copies *",     "copies"),
            ("Description",  "description"),
            ("Location",     "location"),
        ]
        vars_ = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(body, text=label, bg=CLR["bg"], fg=CLR["muted"],
                     font=FONT_SMALL).grid(row=i, column=0, sticky="w", pady=4)
            v = tk.StringVar()
            vars_[key] = v
            entry_field(body, textvariable=v, width=42).grid(
                row=i, column=1, sticky="w", padx=(12, 0), pady=4)

        status = tk.Label(body, text="", bg=CLR["bg"], fg=CLR["danger"],
                          font=FONT_SMALL)
        status.grid(row=len(fields), column=0, columnspan=2, pady=8)

        def submit():
            try:
                self.lib.add_book(
                    self.current_user,
                    isbn=vars_["isbn"].get().strip(),
                    title=vars_["title"].get().strip(),
                    author=vars_["author"].get().strip(),
                    publisher=vars_["publisher"].get().strip() or "Unknown",
                    year=int(vars_["year"].get().strip() or "0"),
                    genre=vars_["genre"].get().strip(),
                    copies=int(vars_["copies"].get().strip() or "1"),
                    description=vars_["description"].get().strip(),
                    location=vars_["location"].get().strip(),
                )
                status.config(fg=CLR["accent2"], text="✅ Book added successfully!")
                for v in vars_.values():
                    v.set("")
            except Exception as e:
                status.config(fg=CLR["danger"], text=str(e))

        styled_btn(body, "➕ Add Book", submit, width=20).grid(
            row=len(fields)+1, column=1, sticky="w", padx=(12, 0))

    # ------------ Delete Book --------------------------------------------------------------------

    def _page_delete_book(self):
        self._clear_content()
        self._page_header("🗑️ Delete Book", "Select a book to remove")

        cols   = ["ID", "Title", "Author", "Avail/Total"]
        widths = [100,  260,     180,      90]
        fr, tv = scrolled_tree(self._content, cols, cols, widths, height=20)
        fr.pack(fill="both", expand=True, padx=16, pady=12)

        for b in sorted(self.lib._books.values(), key=lambda x: x.title):
            tv.insert("", "end", values=(
                b.book_id, b.title, b.author,
                f"{b.available_copies}/{b.total_copies}"))

        def delete_selected():
            sel = tv.selection()
            if not sel:
                messagebox.showwarning("Select", "Please select a book.")
                return
            book_id = tv.item(sel[0])["values"][0]
            title   = tv.item(sel[0])["values"][1]
            if not messagebox.askyesno("Confirm", f"Delete '{title}'?"):
                return
            try:
                self.lib.delete_book(self.current_user, book_id)
                tv.delete(sel[0])
                messagebox.showinfo("Deleted", f"'{title}' deleted.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        styled_btn(self._content, "🗑️ Delete Selected", delete_selected,
                   color=CLR["danger"], width=24).pack(pady=8)

    # -------------- Edit Book --------------------------------------------------------------------

    def _page_edit_book(self):
        self._clear_content()
        self._page_header("✏️ Edit Book", "Select a book then edit fields")

        top = tk.Frame(self._content, bg=CLR["bg"])
        top.pack(fill="both", expand=True)

        cols   = ["ID", "Title", "Author", "Genre", "Year"]
        widths = [100,  240,     180,      110,     60]
        fr, tv = scrolled_tree(top, cols, cols, widths, height=10)
        fr.pack(fill="x", padx=16, pady=8)

        for b in sorted(self.lib._books.values(), key=lambda x: x.title):
            tv.insert("", "end", values=(b.book_id, b.title, b.author, b.genre, b.year))

        edit_frame = tk.Frame(top, bg=CLR["bg"], padx=24, pady=12)
        edit_frame.pack(fill="x")

        fields = ["title", "author", "publisher", "genre", "year", "description", "location"]
        evars = {f: tk.StringVar() for f in fields}

        for i, f in enumerate(fields):
            tk.Label(edit_frame, text=f.capitalize(), bg=CLR["bg"],
                     fg=CLR["muted"], font=FONT_SMALL).grid(
                row=i // 3, column=(i % 3) * 2, sticky="w", padx=6, pady=4)
            entry_field(edit_frame, textvariable=evars[f], width=22).grid(
                row=i // 3, column=(i % 3) * 2 + 1, padx=4, pady=4)

        selected_id = tk.StringVar()
        info_lbl = tk.Label(edit_frame, text="", bg=CLR["bg"], fg=CLR["muted"],
                            font=FONT_SMALL)
        info_lbl.grid(row=3, column=0, columnspan=6, sticky="w", padx=6)

        def on_select(_):
            sel = tv.selection()
            if not sel:
                return
            book_id = tv.item(sel[0])["values"][0]
            book = self.lib._books.get(book_id)
            if not book:
                return
            selected_id.set(book_id)
            for f in fields:
                evars[f].set(getattr(book, f, "") or "")
            info_lbl.config(text=f"Editing: {book.title}")

        tv.bind("<<TreeviewSelect>>", on_select)

        status = tk.Label(edit_frame, text="", bg=CLR["bg"],
                          fg=CLR["danger"], font=FONT_SMALL)
        status.grid(row=4, column=0, columnspan=6, sticky="w", padx=6)

        def save_edit():
            if not selected_id.get():
                status.config(fg=CLR["danger"], text="Select a book first.")
                return
            updates = {f: evars[f].get().strip() for f in fields if evars[f].get().strip()}
            if "year" in updates:
                try:
                    updates["year"] = int(updates["year"])
                except ValueError:
                    status.config(fg=CLR["danger"], text="Year must be a number.")
                    return
            try:
                self.lib.update_book(self.current_user, selected_id.get(), **updates)
                status.config(fg=CLR["accent2"], text="✅ Book updated.")
            except Exception as e:
                status.config(fg=CLR["danger"], text=str(e))

        styled_btn(edit_frame, "💾 Save Changes", save_edit, width=18).grid(
            row=5, column=0, columnspan=2, sticky="w", padx=6, pady=8)

    # ----------- Borrow ----------------------------------------------------------------

    def _page_borrow(self):
        self._clear_content()
        self._page_header("📖 Borrow a Book", "Select an available book")

        cols   = ["ID", "Title", "Author", "Genre", "Available"]
        widths = [100,  240,     180,      110,     80]
        fr, tv = scrolled_tree(self._content, cols, cols, widths, height=18)
        fr.pack(fill="both", expand=True, padx=16, pady=8)

        for b in sorted(self.lib._books.values(), key=lambda x: x.title):
            if b.available_copies > 0:
                tv.insert("", "end", values=(
                    b.book_id, b.title, b.author, b.genre,
                    f"{b.available_copies}/{b.total_copies}"),
                    tags=("ok",))
        tv.tag_configure("ok", foreground=CLR["accent2"])

        bot = tk.Frame(self._content, bg=CLR["bg"], padx=16, pady=8)
        bot.pack(fill="x")
        status = tk.Label(bot, text="", bg=CLR["bg"], fg=CLR["danger"], font=FONT_SMALL)

        on_behalf = tk.StringVar()
        if has_permission(self.current_user, "process_return"):
            tk.Label(bot, text="On behalf of (user_id):", bg=CLR["bg"],
                     fg=CLR["muted"], font=FONT_SMALL).pack(side="left", padx=4)
            entry_field(bot, textvariable=on_behalf, width=18).pack(side="left", padx=4)

        def borrow():
            sel = tv.selection()
            if not sel:
                messagebox.showwarning("Select", "Select a book first.")
                return
            book_id = tv.item(sel[0])["values"][0]
            try:
                import io
                sys.stdout = io.StringIO()
                rec = self.lib.borrow_book(
                    self.current_user, book_id,
                    on_behalf.get().strip() or None)
                sys.stdout = sys.__stdout__
                messagebox.showinfo("Borrowed",
                    f"Borrowed successfully!\nRecord: {rec.record_id}\nDue: {rec.due_date}")
                self._page_borrow()
            except Exception as e:
                sys.stdout = sys.__stdout__
                status.config(text=str(e))
                status.pack()

        styled_btn(bot, "📖 Borrow Selected", borrow, width=22).pack(side="left", padx=8)
        status.pack(side="left")

    # ------- Return ------------------------------------------------------------------------

    def _page_return(self):
        self._clear_content()
        self._page_header("🔄 Return a Book", "Your active borrows")

        records = [r for r in self.lib._borrow_records.values()
                   if not r.is_returned and r.user_id == self.current_user.user_id]
        if has_permission(self.current_user, "process_return"):
            records = [r for r in self.lib._borrow_records.values()
                       if not r.is_returned]

        cols   = ["Record ID", "User",   "Book Title",          "Borrowed",  "Due",       "Status"]
        widths = [110,          120,      220,                   95,          95,          90]
        fr, tv = scrolled_tree(self._content, cols, cols, widths, height=18)
        fr.pack(fill="both", expand=True, padx=16, pady=8)

        today = date.today()
        for r in sorted(records, key=lambda x: x.due_date):
            user = self.lib._users.get(r.user_id)
            book = self.lib._books.get(r.book_id)
            uname = user.username if user else r.user_id
            btitle = book.title if book else r.book_id
            overdue = r.due_date < today
            tag = "over" if overdue else "ok"
            status = f"⚠️ {(today-r.due_date).days}d overdue" if overdue else "Active"
            tv.insert("", "end", values=(r.record_id, uname, btitle,
                                          str(r.borrow_date), str(r.due_date), status),
                      tags=(tag,))
        tv.tag_configure("over", foreground=CLR["danger"])
        tv.tag_configure("ok",   foreground=CLR["text"])

        bot = tk.Frame(self._content, bg=CLR["bg"], padx=16, pady=8)
        bot.pack(fill="x")
        status_lbl = tk.Label(bot, text="", bg=CLR["bg"],
                               fg=CLR["danger"], font=FONT_SMALL)

        def do_return():
            sel = tv.selection()
            if not sel:
                messagebox.showwarning("Select", "Select a record first.")
                return
            record_id = tv.item(sel[0])["values"][0]
            try:
                import io
                sys.stdout = io.StringIO()
                rec = self.lib.return_book(self.current_user, record_id)
                sys.stdout = sys.__stdout__
                fine_msg = f"\nFine charged: ₹{rec.fine:.2f}" if rec.fine > 0 else "\nNo fine!"
                messagebox.showinfo("Returned", f"Book returned.{fine_msg}")
                self._page_return()
            except Exception as e:
                sys.stdout = sys.__stdout__
                status_lbl.config(text=str(e))
                status_lbl.pack()

        styled_btn(bot, "🔄 Return Selected", do_return, width=22).pack(side="left", padx=8)
        status_lbl.pack(side="left")

    # ------ Reserve ------------------------------------------------

    def _page_reserve(self):
        self._clear_content()
        self._page_header("🔒 Reserve a Book", "Hold a book that may be unavailable")

        cols   = ["ID", "Title", "Author", "Available"]
        widths = [100,  260,     180,      90]
        fr, tv = scrolled_tree(self._content, cols, cols, widths, height=20)
        fr.pack(fill="both", expand=True, padx=16, pady=8)

        for b in sorted(self.lib._books.values(), key=lambda x: x.title):
            tv.insert("", "end", values=(
                b.book_id, b.title, b.author,
                f"{b.available_copies}/{b.total_copies}"))

        status_lbl = tk.Label(self._content, text="", bg=CLR["bg"],
                               fg=CLR["danger"], font=FONT_SMALL)

        def reserve():
            sel = tv.selection()
            if not sel:
                messagebox.showwarning("Select", "Select a book first.")
                return
            book_id = tv.item(sel[0])["values"][0]
            try:
                import io
                sys.stdout = io.StringIO()
                res = self.lib.reserve_book(self.current_user, book_id)
                sys.stdout = sys.__stdout__
                messagebox.showinfo("Reserved",
                    f"Reservation: {res.reservation_id}\nExpires: {res.expires_at.strftime('%Y-%m-%d %H:%M')}")
            except Exception as e:
                sys.stdout = sys.__stdout__
                status_lbl.config(text=str(e))
                status_lbl.pack()

        styled_btn(self._content, "🔒 Reserve Selected", reserve, width=24).pack(pady=4)
        status_lbl.pack()

    # -------------------- My History -------------------------------------------------------

    def _page_my_history(self):
        self._clear_content()
        self._page_header("📋 My Borrow History")

        records = [r for r in self.lib._borrow_records.values()
                   if r.user_id == self.current_user.user_id]
        self._show_records_table(records)

    def _page_all_history(self):
        self._clear_content()
        self._page_header("📋 All Borrow History")

        top = tk.Frame(self._content, bg=CLR["bg"], padx=16, pady=8)
        top.pack(fill="x")
        active_v = tk.BooleanVar()
        tk.Checkbutton(top, text="Active only", variable=active_v,
                       bg=CLR["bg"], fg=CLR["text"], selectcolor=CLR["bg"],
                       font=FONT_SMALL, command=lambda: self._page_all_history()).pack(side="left")

        records = list(self.lib._borrow_records.values())
        if active_v.get():
            records = [r for r in records if not r.is_returned]
        self._show_records_table(records)

    def _show_records_table(self, records):
        cols   = ["Record ID", "User",  "Book",     "Borrowed",  "Due",       "Returned",  "Fine",   "Status"]
        widths = [110,          110,     200,         95,          95,          95,          70,       90]
        fr, tv = scrolled_tree(self._content, cols, cols, widths, height=20)
        fr.pack(fill="both", expand=True, padx=16, pady=8)

        for r in sorted(records, key=lambda x: x.borrow_date, reverse=True):
            user = self.lib._users.get(r.user_id)
            book = self.lib._books.get(r.book_id)
            uname  = user.username if user else r.user_id
            btitle = book.title[:30] if book else r.book_id
            ret    = str(r.return_date) if r.return_date else "—"
            status = "✅ Returned" if r.is_returned else "📖 Active"
            tag    = "ret" if r.is_returned else ("over" if r.due_date < date.today() else "ok")
            tv.insert("", "end", values=(
                r.record_id, uname, btitle,
                str(r.borrow_date), str(r.due_date),
                ret, f"₹{r.fine:.0f}", status), tags=(tag,))
        tv.tag_configure("ret",  foreground=CLR["muted"])
        tv.tag_configure("over", foreground=CLR["danger"])
        tv.tag_configure("ok",   foreground=CLR["text"])

    # ------- Recommendations ---------------------------------------------------------------

    def _page_recommendations(self):
        self._clear_content()
        self._page_header("✨ Book Recommendations",
                          f"Personalised picks for {self.current_user.full_name}")

        from recommender import recommend_books
        recs = recommend_books(self.lib, self.current_user, top_n=10)

        if not recs:
            lbl(self._content, "No recommendations available right now!",
                fg=CLR["muted"]).pack(pady=40)
            return

        container = tk.Frame(self._content, bg=CLR["bg"])
        container.pack(fill="both", expand=True, padx=24, pady=12)

        for i, book in enumerate(recs):
            card = tk.Frame(container, bg=CLR["card"], padx=16, pady=12)
            card.pack(fill="x", pady=6)
            tk.Label(card, text=f"{i+1}. {book.title}",
                     bg=CLR["card"], fg=CLR["text"],
                     font=("Segoe UI", 11, "bold")).pack(anchor="w")
            tk.Label(card, text=f"{book.author}  •  {book.genre}  •  {book.year}",
                     bg=CLR["card"], fg=CLR["muted"], font=FONT_SMALL).pack(anchor="w")
            tk.Label(card,
                     text=f"Available: {book.available_copies}/{book.total_copies}  Shelf: {book.location or 'N/A'}",
                     bg=CLR["card"], fg=CLR["accent2"], font=FONT_SMALL).pack(anchor="w")
            if book.description:
                tk.Label(card, text=book.description[:120] + "…",
                         bg=CLR["card"], fg=CLR["muted"], font=FONT_SMALL,
                         wraplength=700, anchor="w").pack(anchor="w")

    # ----------------- Users --------------------------------------------------------------------------

    def _page_users(self):
        self._clear_content()
        self._page_header("👥 User Management")

        cols   = ["User ID", "Username", "Role", "Full Name", "Email", "Fine", "Active", "Borrows"]
        widths = [105,        110,        70,     160,         180,     70,     60,       65]
        fr, tv = scrolled_tree(self._content, cols, cols, widths, height=18)
        fr.pack(fill="both", expand=True, padx=16, pady=8)

        for u in sorted(self.lib._users.values(), key=lambda x: x.username):
            active = "✅" if u.is_active else "❌"
            tv.insert("", "end", values=(
                u.user_id, u.username, u.role.value, u.full_name,
                u.email, f"₹{u.fine_amount:.0f}", active, len(u.borrowed_books)))

        bot = tk.Frame(self._content, bg=CLR["bg"], padx=16, pady=6)
        bot.pack(fill="x")

        def toggle_status():
            sel = tv.selection()
            if not sel:
                return
            uid = tv.item(sel[0])["values"][0]
            try:
                self.lib.toggle_user_status(self.current_user, uid)
                self._page_users()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        def delete_user():
            sel = tv.selection()
            if not sel:
                return
            uid   = tv.item(sel[0])["values"][0]
            uname = tv.item(sel[0])["values"][1]
            if not messagebox.askyesno("Confirm", f"Delete user '{uname}'?"):
                return
            try:
                self.lib.delete_user(self.current_user, uid)
                self._page_users()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        if has_permission(self.current_user, "update_any_user"):
            styled_btn(bot, "🔀 Toggle Active", toggle_status,
                       color=CLR["warn"], width=18).pack(side="left", padx=4)
        if has_permission(self.current_user, "delete_user"):
            styled_btn(bot, "🗑️ Delete User", delete_user,
                       color=CLR["danger"], width=16).pack(side="left", padx=4)

    # ------ Create User -----------------------------------------------------------

    def _page_create_user(self):
        self._clear_content()
        self._page_header("👤 Create New User")

        body = tk.Frame(self._content, bg=CLR["bg"], padx=36, pady=24)
        body.pack(fill="both", expand=True)

        fields = [
            ("Username *",  "username", False),
            ("Password *",  "password", True),
            ("Full Name *", "full_name", False),
            ("Email *",     "email",    False),
            ("Phone",       "phone",    False),
        ]
        vars_ = {}
        for i, (label, key, secret) in enumerate(fields):
            tk.Label(body, text=label, bg=CLR["bg"], fg=CLR["muted"],
                     font=FONT_SMALL).grid(row=i, column=0, sticky="w", pady=4)
            v = tk.StringVar()
            vars_[key] = v
            entry_field(body, textvariable=v, show="•" if secret else None, width=36).grid(
                row=i, column=1, sticky="w", padx=12, pady=4)

        tk.Label(body, text="Role *", bg=CLR["bg"], fg=CLR["muted"],
                 font=FONT_SMALL).grid(row=len(fields), column=0, sticky="w", pady=4)
        role_var = tk.StringVar(value="user")
        roles = ["user", "staff"] + (["admin"] if self.current_user.role == Role.ADMIN else [])
        role_cb = ttk.Combobox(body, textvariable=role_var, values=roles,
                                state="readonly", width=14)
        role_cb.grid(row=len(fields), column=1, sticky="w", padx=12, pady=4)

        status = tk.Label(body, text="", bg=CLR["bg"], fg=CLR["danger"], font=FONT_SMALL)
        status.grid(row=len(fields)+1, column=0, columnspan=2, pady=6)

        def create():
            try:
                self.lib.create_user(
                    self.current_user,
                    username=vars_["username"].get().strip(),
                    password=vars_["password"].get(),
                    role=Role(role_var.get()),
                    full_name=vars_["full_name"].get().strip(),
                    email=vars_["email"].get().strip(),
                    phone=vars_["phone"].get().strip(),
                )
                status.config(fg=CLR["accent2"], text="✅ User created!")
                for v in vars_.values():
                    v.set("")
            except Exception as e:
                status.config(fg=CLR["danger"], text=str(e))

        styled_btn(body, "👤 Create User", create, width=20).grid(
            row=len(fields)+2, column=1, sticky="w", padx=12, pady=4)

    # ----------------- Registrations -------------------------------------------------------------------------

    def _page_registrations(self):
        self._clear_content()
        self._page_header("📥 Pending Registrations")

        reqs = list(self.lib._pending_registrations.values())
        cols   = ["Reg ID", "Username", "Full Name", "Email", "Requested At"]
        widths = [120,       120,        160,         200,     160]
        fr, tv = scrolled_tree(self._content, cols, cols, widths, height=18)
        fr.pack(fill="both", expand=True, padx=16, pady=8)

        for r in reqs:
            tv.insert("", "end", values=(
                r["reg_id"], r["username"], r["full_name"],
                r["email"], r["requested_at"][:19]))

        bot = tk.Frame(self._content, bg=CLR["bg"], padx=16, pady=6)
        bot.pack(fill="x")

        def approve():
            sel = tv.selection()
            if not sel:
                return
            reg_id = tv.item(sel[0])["values"][0]
            try:
                self.lib.approve_registration(self.current_user, reg_id)
                self._page_registrations()
                messagebox.showinfo("Approved", "Registration approved!")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        def reject():
            sel = tv.selection()
            if not sel:
                return
            reg_id = tv.item(sel[0])["values"][0]
            if messagebox.askyesno("Confirm", "Reject this registration?"):
                try:
                    self.lib.reject_registration(self.current_user, reg_id)
                    self._page_registrations()
                except Exception as e:
                    messagebox.showerror("Error", str(e))

        styled_btn(bot, "✅ Approve", approve, color=CLR["accent2"], width=14).pack(
            side="left", padx=4)
        styled_btn(bot, "❌ Reject", reject, color=CLR["danger"], width=14).pack(
            side="left", padx=4)

    # ---------------- Fines ----------------------------------------------------------------

    def _page_fines(self):
        self._clear_content()
        self._page_header("💰 Fine Management")

        users = [u for u in self.lib._users.values() if u.fine_amount > 0]
        cols   = ["User ID", "Username", "Full Name", "Fine Amount"]
        widths = [110,        120,        180,         100]
        fr, tv = scrolled_tree(self._content, cols, cols, widths, height=16)
        fr.pack(fill="both", expand=True, padx=16, pady=8)

        for u in sorted(users, key=lambda x: -x.fine_amount):
            tv.insert("", "end", values=(
                u.user_id, u.username, u.full_name, f"₹{u.fine_amount:.2f}"),
                tags=("fine",))
        tv.tag_configure("fine", foreground=CLR["danger"])

        bot = tk.Frame(self._content, bg=CLR["bg"], padx=16, pady=6)
        bot.pack(fill="x")

        if has_permission(self.current_user, "collect_fine"):
            def collect():
                sel = tv.selection()
                if not sel:
                    return
                uid  = tv.item(sel[0])["values"][0]
                fine = tv.item(sel[0])["values"][3]
                amt  = simpledialog.askfloat("Collect Fine",
                    f"Outstanding: {fine}\nAmount to collect (₹):", minvalue=0.01)
                if amt is None:
                    return
                try:
                    self.lib.collect_fine(self.current_user, uid, amt)
                    self._page_fines()
                except Exception as e:
                    messagebox.showerror("Error", str(e))

            styled_btn(bot, "💳 Collect Fine", collect, color=CLR["accent"], width=18).pack(
                side="left", padx=4)

        if has_permission(self.current_user, "waive_fine"):
            def waive():
                sel = tv.selection()
                if not sel:
                    return
                uid   = tv.item(sel[0])["values"][0]
                uname = tv.item(sel[0])["values"][1]
                if messagebox.askyesno("Confirm", f"Waive all fines for '{uname}'?"):
                    try:
                        self.lib.waive_fine(self.current_user, uid)
                        self._page_fines()
                    except Exception as e:
                        messagebox.showerror("Error", str(e))

            styled_btn(bot, "🎁 Waive Fine", waive, color=CLR["warn"], width=16).pack(
                side="left", padx=4)

    # ------------------------ Overdue Report -------------------------------------------------------------------------------

    def _page_overdue(self):
        self._clear_content()
        self._page_header("📛 Overdue Books Report")

        from analytics import overdue_report
        rows = overdue_report(self.lib)

        cols   = ["Record ID", "User",   "Book Title",           "Due Date",  "Days Overdue", "Accrued Fine"]
        widths = [110,          120,      220,                    95,          100,             100]
        fr, tv = scrolled_tree(self._content, cols, cols, widths, height=18)
        fr.pack(fill="both", expand=True, padx=16, pady=8)

        total_fine = 0.0
        for r, user, book, days, fine in rows:
            uname  = user.username if user else r.user_id
            btitle = book.title    if book else r.book_id
            tv.insert("", "end", values=(
                r.record_id, uname, btitle,
                str(r.due_date), f"{days} days", f"₹{fine:.2f}"), tags=("over",))
            total_fine += fine
        tv.tag_configure("over", foreground=CLR["danger"])

        lbl(self._content,
            f"  {len(rows)} overdue book(s)   |   Total accrued fines: ₹{total_fine:.2f}",
            fg=CLR["warn"]).pack(anchor="w", padx=16, pady=4)

    # ----------------------- Send Alerts ------------------------------------------------------------

    def _do_send_alerts(self):
        try:
            import io
            sys.stdout = io.StringIO()
            cnt = self.lib.send_overdue_alerts(self.current_user)
            sys.stdout = sys.__stdout__
            messagebox.showinfo("Alerts Sent", f"{cnt} overdue alert(s) dispatched.")
        except Exception as e:
            sys.stdout = sys.__stdout__
            messagebox.showerror("Error", str(e))

    # ------------------------------ Dashboard -------------------------------------------------------------------------

    def _page_dashboard(self):
        self._clear_content()
        self._page_header("📊 Analytics Dashboard", "Aggregated library statistics")

        from analytics import overdue_report
        from collections import Counter

        books   = list(self.lib._books.values())
        users   = list(self.lib._users.values())
        records = list(self.lib._borrow_records.values())

        total_copies = sum(b.total_copies   for b in books)
        avail_copies = sum(b.available_copies for b in books)
        borrowed     = total_copies - avail_copies
        overdue_rows = overdue_report(self.lib)
        total_fines  = sum(u.fine_amount for u in users)

        # ----------- KPI cards --------------------------------------------
        kpi_row = tk.Frame(self._content, bg=CLR["bg"])
        kpi_row.pack(fill="x", padx=16, pady=12)

        kpis = [
            ("Titles",          len(books),            CLR["accent"]),
            ("Users",           len(users),            CLR["accent"]),
            ("Active Borrows",  borrowed,              CLR["warn"]),
            ("Overdue",         len(overdue_rows),     CLR["danger"]),
            ("Outstanding ₹",   f"{total_fines:.0f}",  CLR["danger"]),
            ("Available",       avail_copies,           CLR["accent2"]),
        ]
        for label, val, col in kpis:
            card = tk.Frame(kpi_row, bg=CLR["card"], padx=14, pady=12)
            card.pack(side="left", padx=6, fill="y")
            tk.Label(card, text=str(val), bg=CLR["card"], fg=col,
                     font=("Segoe UI", 20, "bold")).pack()
            tk.Label(card, text=label, bg=CLR["card"], fg=CLR["muted"],
                     font=FONT_SMALL).pack()

        nb = ttk.Notebook(self._content)
        nb.pack(fill="both", expand=True, padx=16, pady=8)

        style = ttk.Style()
        style.configure("TNotebook",          background=CLR["bg"],
                         borderwidth=0)
        style.configure("TNotebook.Tab",      background=CLR["card"],
                         foreground=CLR["muted"],
                         padding=[12, 6], font=FONT_SMALL)
        style.map("TNotebook.Tab",
                  background=[("selected", CLR["accent"])],
                  foreground=[("selected", CLR["bg"])])

        # -------------- Top Borrowed -------------------------------------------------------
        t1 = tk.Frame(nb, bg=CLR["bg"])
        nb.add(t1, text="🏆 Top Books")
        freq = Counter(r.book_id for r in records)
        cols   = ["Rank", "Title",  "Author", "Genre",  "Borrows"]
        widths = [55,      240,      160,      100,      70]
        fr, tv = scrolled_tree(t1, cols, cols, widths, height=16)
        fr.pack(fill="both", expand=True, padx=8, pady=8)
        for rank, (bid, cnt) in enumerate(freq.most_common(20), 1):
            b = self.lib._books.get(bid)
            tv.insert("", "end", values=(rank, b.title if b else bid,
                b.author if b else "—", b.genre if b else "—", cnt))

        # ------------ Top Borrowers -----------------------------------------------------------------------------
        t2 = tk.Frame(nb, bg=CLR["bg"])
        nb.add(t2, text="📚 Top Users")
        ufreq = Counter(r.user_id for r in records)
        cols   = ["Rank", "Username", "Full Name", "Borrows", "Fine"]
        widths = [55,      120,        160,          70,        80]
        fr, tv = scrolled_tree(t2, cols, cols, widths, height=16)
        fr.pack(fill="both", expand=True, padx=8, pady=8)
        for rank, (uid, cnt) in enumerate(ufreq.most_common(20), 1):
            u = self.lib._users.get(uid)
            tv.insert("", "end", values=(rank, u.username if u else uid,
                u.full_name if u else "—", cnt,
                f"₹{u.fine_amount:.2f}" if u else "—"))

        # --------------------- Genre Distribution -----------------------------------
        t3 = tk.Frame(nb, bg=CLR["bg"])
        nb.add(t3, text="📊 Genres")
        gcnt  = Counter(b.genre for b in books)
        gborrow = Counter(self.lib._books[r.book_id].genre
                          for r in records
                          if r.book_id in self.lib._books)
        cols   = ["Genre",  "Titles", "Borrows"]
        widths = [180,       80,       80]
        fr, tv = scrolled_tree(t3, cols, cols, widths, height=16)
        fr.pack(fill="both", expand=True, padx=8, pady=8)
        for g, cnt in gcnt.most_common():
            tv.insert("", "end", values=(g, cnt, gborrow.get(g, 0)))

        # ------------------------- Overdue List ------------------------------------------
        t4 = tk.Frame(nb, bg=CLR["bg"])
        nb.add(t4, text="📛 Overdue")
        cols   = ["Record",  "User",  "Book",  "Due",  "Days", "Fine"]
        widths = [110,        110,     220,      95,     70,     80]
        fr, tv = scrolled_tree(t4, cols, cols, widths, height=16)
        fr.pack(fill="both", expand=True, padx=8, pady=8)
        for r, user, book, days, fine in overdue_rows:
            tv.insert("", "end", values=(
                r.record_id,
                user.username if user else r.user_id,
                book.title    if book else r.book_id,
                str(r.due_date), days, f"₹{fine:.2f}"), tags=("ov",))
        tv.tag_configure("ov", foreground=CLR["danger"])

    # ------------------- Audit Log -----------------------------------------------------------

    def _page_logs(self):
        self._clear_content()
        self._page_header("🗒️ System Audit Log")

        logs = list(reversed(self.lib._logs))

        top = tk.Frame(self._content, bg=CLR["bg"], padx=16, pady=8)
        top.pack(fill="x")
        search_v = tk.StringVar()
        tk.Label(top, text="Filter:", bg=CLR["bg"], fg=CLR["muted"],
                 font=FONT_SMALL).pack(side="left")
        entry_field(top, textvariable=search_v, width=30).pack(side="left", padx=6)

        cols   = ["Timestamp",         "Actor",  "Action",  "Detail"]
        widths = [145,                  110,      120,       380]
        fr, tv = scrolled_tree(self._content, cols, cols, widths, height=22)
        fr.pack(fill="both", expand=True, padx=16, pady=4)

        def populate(q=""):
            for row in tv.get_children():
                tv.delete(row)
            q = q.lower()
            for entry in logs:
                if q and not any(q in str(v).lower() for v in entry.values()):
                    continue
                tv.insert("", "end", values=(
                    entry["timestamp"][:19],
                    entry["actor"],
                    entry["action"],
                    entry["detail"]))

        search_v.trace_add("write", lambda *_: populate(search_v.get()))
        populate()

        lbl(self._content, f"  {len(logs)} total log entries",
            fg=CLR["muted"]).pack(anchor="w", padx=16, pady=2)


# ----------------------------------------- Entry point ----------------------------------------------------

def main():
    app = LibraryApp()
    app.mainloop()
    # Auto-save on exit
    try:
        save_library(app.lib, SAVE_FILE)
    except Exception:
        pass


if __name__ == "__main__":
    main()
