from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from .user_state import sanitize_user_id

PBKDF2_ROUNDS = 240000
SESSION_TTL_SECONDS = 60 * 60 * 24 * 30


@dataclass(slots=True)
class AuthUser:
    user_id: str
    password_salt_b64: str
    password_hash_b64: str
    created_at: float
    last_login_at: float


@dataclass(slots=True)
class AuthSession:
    token: str
    user_id: str
    created_at: float
    last_seen_at: float
    expires_at: float


class AuthStore:
    def __init__(self, users_path: Path, sessions_path: Path) -> None:
        self.users_path = users_path
        self.sessions_path = sessions_path
        self.users_path.parent.mkdir(parents=True, exist_ok=True)
        self.sessions_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._users: dict[str, AuthUser] = {}
        self._sessions: dict[str, AuthSession] = {}
        self._load()

    def _load(self) -> None:
        self._users = self._load_map(self.users_path, self._coerce_user)
        self._sessions = self._load_map(self.sessions_path, self._coerce_session)
        self._prune_expired_sessions()

    def _load_map(self, path: Path, coerce_fn):
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if not isinstance(payload, dict):
            return {}
        result = {}
        for key, raw in payload.items():
            try:
                record = coerce_fn(raw)
            except Exception:
                continue
            result[str(key)] = record
        return result

    def _coerce_user(self, raw: dict) -> AuthUser:
        return AuthUser(
            user_id=sanitize_user_id(str(raw["user_id"])),
            password_salt_b64=str(raw["password_salt_b64"]),
            password_hash_b64=str(raw["password_hash_b64"]),
            created_at=float(raw["created_at"]),
            last_login_at=float(raw.get("last_login_at", 0.0)),
        )

    def _coerce_session(self, raw: dict) -> AuthSession:
        return AuthSession(
            token=str(raw["token"]),
            user_id=sanitize_user_id(str(raw["user_id"])),
            created_at=float(raw["created_at"]),
            last_seen_at=float(raw.get("last_seen_at", raw["created_at"])),
            expires_at=float(raw.get("expires_at", raw["created_at"] + SESSION_TTL_SECONDS)),
        )

    def _save(self) -> None:
        users_payload = {user_id: asdict(user) for user_id, user in self._users.items()}
        sessions_payload = {token: asdict(session) for token, session in self._sessions.items()}
        self.users_path.write_text(json.dumps(users_payload), encoding="utf-8")
        self.sessions_path.write_text(json.dumps(sessions_payload), encoding="utf-8")

    def _prune_expired_sessions(self) -> None:
        now = time.time()
        expired = [token for token, session in self._sessions.items() if session.expires_at <= now]
        for token in expired:
            self._sessions.pop(token, None)

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS, dklen=32)

    @staticmethod
    def _to_b64(value: bytes) -> str:
        return base64.b64encode(value).decode("ascii")

    @staticmethod
    def _from_b64(value: str) -> bytes:
        return base64.b64decode(value.encode("ascii"))

    def register(self, user_id: str, password: str) -> AuthUser:
        safe_user = sanitize_user_id(user_id)
        clean_password = password.strip()
        if len(clean_password) < 4:
            raise ValueError("Password must be at least 4 characters.")

        now = time.time()
        with self._lock:
            if safe_user in self._users:
                raise ValueError("User already exists.")
            salt = os.urandom(16)
            digest = self._hash_password(clean_password, salt)
            user = AuthUser(
                user_id=safe_user,
                password_salt_b64=self._to_b64(salt),
                password_hash_b64=self._to_b64(digest),
                created_at=now,
                last_login_at=now,
            )
            self._users[safe_user] = user
            self._save()
            return user

    def login(self, user_id: str, password: str) -> AuthSession | None:
        safe_user = sanitize_user_id(user_id)
        clean_password = password.strip()
        with self._lock:
            user = self._users.get(safe_user)
            if user is None:
                return None
            salt = self._from_b64(user.password_salt_b64)
            expected = self._from_b64(user.password_hash_b64)
            candidate = self._hash_password(clean_password, salt)
            if not hmac.compare_digest(expected, candidate):
                return None

            now = time.time()
            token = uuid.uuid4().hex
            session = AuthSession(
                token=token,
                user_id=safe_user,
                created_at=now,
                last_seen_at=now,
                expires_at=now + SESSION_TTL_SECONDS,
            )
            self._sessions[token] = session
            user.last_login_at = now
            self._prune_expired_sessions()
            self._save()
            return session

    def get_session(self, token: str) -> AuthSession | None:
        clean_token = (token or "").strip()
        if not clean_token:
            return None
        with self._lock:
            self._prune_expired_sessions()
            session = self._sessions.get(clean_token)
            if session is None:
                self._save()
                return None
            now = time.time()
            session.last_seen_at = now
            session.expires_at = now + SESSION_TTL_SECONDS
            self._save()
            return session

    def logout(self, token: str) -> bool:
        clean_token = (token or "").strip()
        if not clean_token:
            return False
        with self._lock:
            removed = self._sessions.pop(clean_token, None) is not None
            self._save()
            return removed

    def google_login(self, email: str) -> AuthSession:
        safe_user = sanitize_user_id(email.split('@')[0] if '@' in email else email)
        now = time.time()
        with self._lock:
            user = self._users.get(safe_user)
            if user is None:
                user = AuthUser(
                    user_id=safe_user,
                    password_salt_b64=self._to_b64(b"oauth"),
                    password_hash_b64=self._to_b64(b"oauth"),
                    created_at=now,
                    last_login_at=now,
                )
                self._users[safe_user] = user
            else:
                user.last_login_at = now

            token = uuid.uuid4().hex
            session = AuthSession(
                token=token,
                user_id=safe_user,
                created_at=now,
                last_seen_at=now,
                expires_at=now + SESSION_TTL_SECONDS,
            )
            self._sessions[token] = session
            self._prune_expired_sessions()
            self._save()
            return session
