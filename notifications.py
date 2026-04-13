"""
notifications.py - Simulated Notification System (Email / SMS)

In production, replace _send_email / _send_sms with real SMTP / Twilio calls.
All sent notifications are stored in an in-memory log accessible via the admin panel.
"""

from datetime import datetime
from typing import List
from dataclasses import dataclass, field


@dataclass
class Notification:
    notif_id: str
    channel: str          # "email" | "sms" | "system"
    recipient: str        # email address or phone number
    subject: str
    body: str
    sent_at: datetime = field(default_factory=datetime.now)
    delivered: bool = True


class NotificationService:
    """Simulated notification dispatcher with a sent-log."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose          # print to console when True
        self._log: List[Notification] = []
        self._counter = 0

    # ── Internal plumbing ────────────────────────────────────────────────────

    def _next_id(self) -> str:
        self._counter += 1
        return f"N-{self._counter:04d}"

    def _dispatch(self, channel: str, recipient: str, subject: str, body: str):
        n = Notification(
            notif_id=self._next_id(),
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
        )
        self._log.append(n)
        if self.verbose:
            icon = {"email": "📧", "sms": "📱", "system": "🔔"}.get(channel, "📣")
            print(f"  {icon} [{channel.upper()}] → {recipient}")
            print(f"     {subject}")

    # ── Public API ────────────────────────────────────────────────────────────

    def send_welcome(self, full_name: str, username: str, email: str):
        self._dispatch(
            "email", email,
            subject=f"Welcome to the Library, {full_name}!",
            body=(
                f"Hi {full_name},\n\n"
                f"Your library account has been approved.\n"
                f"Username: {username}\n\n"
                f"You can borrow up to 3 books at a time. Happy reading!"
            )
        )

    def send_registration_received(self, full_name: str, email: str):
        self._dispatch(
            "email", email,
            subject="Library Registration Received",
            body=(
                f"Hi {full_name},\n\n"
                f"We've received your registration request. "
                f"An admin will review and approve it shortly."
            )
        )

    def send_registration_rejected(self, full_name: str, email: str):
        self._dispatch(
            "email", email,
            subject="Library Registration Update",
            body=(
                f"Hi {full_name},\n\n"
                f"Unfortunately your registration request was not approved. "
                f"Please visit the library in person for assistance."
            )
        )

    def send_borrow_confirmation(self, full_name: str, email: str,
                                  book_title: str, due_date):
        self._dispatch(
            "email", email,
            subject=f"Book Borrowed: {book_title}",
            body=(
                f"Hi {full_name},\n\n"
                f"You have successfully borrowed '{book_title}'.\n"
                f"Please return it by {due_date}.\n\n"
                f"Late returns incur a fine of ₹5 per day."
            )
        )

    def send_return_confirmation(self, full_name: str, email: str,
                                  book_title: str, fine: float):
        fine_line = f"Fine charged: ₹{fine:.2f}" if fine > 0 else "No fine — returned on time!"
        self._dispatch(
            "email", email,
            subject=f"Book Returned: {book_title}",
            body=(
                f"Hi {full_name},\n\n"
                f"'{book_title}' has been returned successfully.\n"
                f"{fine_line}\n\nThank you!"
            )
        )

    def send_overdue_alert(self, full_name: str, email: str, phone: str,
                           book_title: str, days_overdue: int, fine_so_far: float):
        self._dispatch(
            "email", email,
            subject=f"⚠️ Overdue Notice: {book_title}",
            body=(
                f"Hi {full_name},\n\n"
                f"'{book_title}' is {days_overdue} day(s) overdue.\n"
                f"Current fine: ₹{fine_so_far:.2f}\n\n"
                f"Please return the book as soon as possible."
            )
        )
        if phone:
            self._dispatch(
                "sms", phone,
                subject="Overdue Alert",
                body=f"Library: '{book_title}' is {days_overdue}d overdue. Fine: ₹{fine_so_far:.2f}. Please return ASAP."
            )

    def send_due_reminder(self, full_name: str, email: str,
                           book_title: str, due_date, days_left: int):
        self._dispatch(
            "email", email,
            subject=f"Reminder: '{book_title}' due in {days_left} day(s)",
            body=(
                f"Hi {full_name},\n\n"
                f"Just a reminder that '{book_title}' is due on {due_date} "
                f"({days_left} day(s) from today).\n\n"
                f"Please return or renew it in time."
            )
        )

    def send_reservation_ready(self, full_name: str, email: str, book_title: str):
        self._dispatch(
            "email", email,
            subject=f"Reservation Ready: {book_title}",
            body=(
                f"Hi {full_name},\n\n"
                f"Good news! '{book_title}' is now available for pickup.\n"
                f"Your reservation holds for 48 hours."
            )
        )

    def send_fine_receipt(self, full_name: str, email: str,
                           amount: float, remaining: float):
        self._dispatch(
            "email", email,
            subject="Fine Payment Receipt",
            body=(
                f"Hi {full_name},\n\n"
                f"Payment received: ₹{amount:.2f}\n"
                f"Outstanding balance: ₹{remaining:.2f}\n\nThank you!"
            )
        )

    def send_admin_new_registration(self, admin_email: str,
                                     applicant: str, reg_id: str):
        self._dispatch(
            "system", admin_email,
            subject=f"New Registration Request: {applicant}",
            body=f"A new registration request (ID: {reg_id}) from '{applicant}' is awaiting approval."
        )

    # ── Notification log ─────────────────────────────────────────────────────

    def get_log(self, last_n: int = 20) -> List[Notification]:
        return self._log[-last_n:]

    def print_log(self, last_n: int = 20):
        entries = self.get_log(last_n)
        print(f"\n{'─'*80}")
        print(f"  📣 NOTIFICATION LOG (last {last_n})")
        print(f"{'─'*80}")
        if not entries:
            print("  No notifications sent yet.")
        for n in entries:
            ts = n.sent_at.strftime("%Y-%m-%d %H:%M")
            icon = {"email": "📧", "sms": "📱", "system": "🔔"}.get(n.channel, "📣")
            print(f"  {n.notif_id:<8} [{ts}] {icon} {n.channel:<6} → {n.recipient:<30} {n.subject[:35]}")
        print(f"{'─'*80}\n")

    @property
    def total_sent(self) -> int:
        return len(self._log)
