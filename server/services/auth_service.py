import re
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)
from psycopg.errors import UniqueViolation

from server.repositories.user_repository import UserRepository
from server.services.session_service import SessionService


class AuthenticationError(Exception):
    """Ошибка регистрации или авторизации."""


class AuthService:
    """Сервис регистрации и авторизации пользователей."""

    def __init__(
        self,
        user_repository: UserRepository | None = None,
        session_service: SessionService | None = None,
    ) -> None:
        self._users = user_repository or UserRepository()
        self.sessions = session_service or SessionService()
        self._password_hasher = PasswordHasher()

    @staticmethod
    def _validate_registration_data(
        username: Any,
        password: Any,
        full_name: Any,
    ) -> tuple[str, str, str]:
        if not all(
            isinstance(value, str)
            for value in (username, password, full_name)
        ):
            raise AuthenticationError(
                "Логин, пароль и ФИО должны быть строками."
            )

        username = username.strip().lower()
        full_name = full_name.strip()

        if not re.fullmatch(r"[a-zA-Z0-9_.-]{3,32}", username):
            raise AuthenticationError(
                "Логин должен содержать от 3 до 32 символов: "
                "латинские буквы, цифры, точку, дефис или подчёркивание."
            )

        if len(password) < 8 or len(password) > 128:
            raise AuthenticationError(
                "Пароль должен содержать от 8 до 128 символов."
            )

        if len(full_name) < 2 or len(full_name) > 120:
            raise AuthenticationError(
                "ФИО должно содержать от 2 до 120 символов."
            )

        return username, password, full_name

    def register(
        self,
        username: Any,
        password: Any,
        full_name: Any,
    ) -> dict[str, Any]:
        username, password, full_name = (
            self._validate_registration_data(
                username,
                password,
                full_name,
            )
        )

        password_hash = self._password_hasher.hash(password)

        try:
            return self._users.create(
                username=username,
                password_hash=password_hash,
                full_name=full_name,
            )
        except UniqueViolation as error:
            raise AuthenticationError(
                "Пользователь с таким логином уже существует."
            ) from error

    def login(
        self,
        username: Any,
        password: Any,
    ) -> dict[str, Any]:
        if not isinstance(username, str) or not isinstance(password, str):
            raise AuthenticationError("Укажите логин и пароль.")

        username = username.strip().lower()

        if not username or not password:
            raise AuthenticationError("Укажите логин и пароль.")

        user = self._users.get_by_username(username)

        if user is None:
            raise AuthenticationError("Неверный логин или пароль.")

        try:
            password_is_valid = self._password_hasher.verify(
                user["password_hash"],
                password,
            )
        except (
            VerifyMismatchError,
            VerificationError,
            InvalidHashError,
        ):
            password_is_valid = False

        if not password_is_valid:
            raise AuthenticationError("Неверный логин или пароль.")

        public_user = {
            "id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"],
        }

        token = self.sessions.create_session(public_user)

        return {
            "token": token,
            "user": public_user,
        }

    def logout(self, token: Any) -> bool:
        if not isinstance(token, str) or not token:
            raise AuthenticationError("Не указан токен сессии.")

        if not self.sessions.delete_session(token):
            raise AuthenticationError("Сессия не найдена или уже завершена.")

        return True