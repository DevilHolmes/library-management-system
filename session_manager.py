"""
session_manager.py - Multi-Session Tracking with Timeout Enforcement

Tracks all active login sessions, enforces per-user session limits,
and automatically expires stale sessions based on config.SESSION_TIMEOUT_MINUTES.

Usage:
    sm = SessionManager()
    token = sm.create_session(user)
    user  = sm.validate_token(token)   # raises SessionExpiredError if stale
    sm.end_session(token)
"""

import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass, field

from models import User
from config import config
from exceptions import SessionExpiredError, AuthenticationError


@dataclass
class Session:
    token: str
    user_id: str
    username: str
    role: str
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    ip_address: str = "127.0.0.1"
    user_agent: str = "CLI"

    def is_expired(self) -> bool:
        if config.SESSION_TIMEOUT_MINUTES == 0:
            return False
        cutoff = self.last_active + timedelta(minutes=config.SESSION_TIMEOUT_MINUTES)
        return datetime.now() > cutoff

    def touch(self):
        """Refresh last-active timestamp."""
        self.last_active = datetime.now()

    def age_minutes(self) -> float:
        return (datetime.now() - self.created_at).total_seconds() / 60


class SessionManager:
    """Thread-safe session store (single-process; use Redis for multi-process)."""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}   # token -> Session

    # ── Core API ──────────────────────────────────────────────────────────────

    def create_session(self, user: User,
                       ip: str = "127.0.0.1",
                       agent: str = "CLI") -> str:
        """Create a new session for user. Enforces MAX_SESSIONS_PER_USER."""
        self._expire_stale()

        # Enforce per-user session limit
        if config.MAX_SESSIONS_PER_USER > 0:
            user_sessions = [s for s in self._sessions.values()
                             if s.user_id == user.user_id]
            while len(user_sessions) >= config.MAX_SESSIONS_PER_USER:
                # Evict oldest session
                oldest = min(user_sessions, key=lambda s: s.created_at)
                del self._sessions[oldest.token]
                user_sessions.remove(oldest)

        token = secrets.token_hex(32)
        session = Session(
            token=token,
            user_id=user.user_id,
            username=user.username,
            role=user.role.value,
            ip_address=ip,
            user_agent=agent,
        )
        self._sessions[token] = session
        return token

    def validate_token(self, token: str) -> Session:
        """Return session if valid, raise SessionExpiredError if expired/missing."""
        session = self._sessions.get(token)
        if not session:
            raise SessionExpiredError()
        if session.is_expired():
            del self._sessions[token]
            raise SessionExpiredError()
        session.touch()
        return session

    def end_session(self, token: str):
        """Explicitly log out a session."""
        self._sessions.pop(token, None)

    def end_all_sessions(self, user_id: str):
        """Force-logout all sessions for a given user (e.g. after deactivation)."""
        to_remove = [t for t, s in self._sessions.items() if s.user_id == user_id]
        for t in to_remove:
            del self._sessions[t]

    # ── Queries ───────────────────────────────────────────────────────────────

    def active_sessions(self) -> list[Session]:
        self._expire_stale()
        return list(self._sessions.values())

    def sessions_for_user(self, user_id: str) -> list[Session]:
        return [s for s in self._sessions.values() if s.user_id == user_id]

    def count(self) -> int:
        self._expire_stale()
        return len(self._sessions)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _expire_stale(self):
        expired = [t for t, s in self._sessions.items() if s.is_expired()]
        for t in expired:
            del self._sessions[t]

    # ── Display ───────────────────────────────────────────────────────────────

    def print_sessions(self):
        self._expire_stale()
        sessions = list(self._sessions.values())
        print(f"\n{'─'*80}")
        print(f"  🔐 ACTIVE SESSIONS ({len(sessions)})")
        print(f"{'─'*80}")
        if not sessions:
            print("  No active sessions.")
        else:
            print(f"  {'Token':<20} {'Username':<16} {'Role':<8} {'Age(m)':<8} {'IP':<16} {'Agent'}")
            print(f"  {'─'*76}")
            for s in sorted(sessions, key=lambda x: x.created_at):
                tok = s.token[:16] + "…"
                age = f"{s.age_minutes():.1f}"
                print(f"  {tok:<20} {s.username:<16} {s.role:<8} {age:<8} {s.ip_address:<16} {s.user_agent}")
        print(f"{'─'*80}\n")


# ── Module-level singleton ────────────────────────────────────────────────────
session_manager = SessionManager()
