from typing import Any

from psycopg.rows import dict_row

from server.database.connection import get_connection


class UserRepository:
    """Репозиторий для работы с пользователями."""

    def get_by_username(self, username: str) -> dict[str, Any] | None:
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT id, username, password_hash, full_name, role
                    FROM users
                    WHERE username = %s;
                    """,
                    (username,),
                )
                user = cursor.fetchone()

        return dict(user) if user else None

    def create(
        self,
        username: str,
        password_hash: str,
        full_name: str,
    ) -> dict[str, Any]:
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (
                        username,
                        password_hash,
                        full_name,
                        role
                    )
                    VALUES (%s, %s, %s, 'user')
                    RETURNING id, username, full_name, role;
                    """,
                    (username, password_hash, full_name),
                )
                user = cursor.fetchone()

        return dict(user)