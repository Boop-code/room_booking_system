import secrets
from threading import Lock
from typing import Any


class SessionService:
    """Управляет активными сессиями пользователей."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def create_session(self, user: dict[str, Any]) -> str:
        token = secrets.token_urlsafe(32)

        session_data = {
            "user_id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"],
        }

        with self._lock:
            self._sessions[token] = session_data

        return token

    def get_user(self, token: str) -> dict[str, Any] | None:
        with self._lock:
            user = self._sessions.get(token)
            return dict(user) if user else None

    def delete_session(self, token: str) -> bool:
        with self._lock:
            return self._sessions.pop(token, None) is not None