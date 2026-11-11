from datetime import datetime
from typing import Any

from psycopg.rows import dict_row

from server.database.connection import get_connection


class AuditRepository:
    """Репозиторий для чтения журнала действий."""

    def get_entries(
        self,
        limit: int = 100,
        offset: int = 0,
        action: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Возвращает записи журнала с фильтрами и пагинацией."""

        conditions: list[str] = []
        parameters: list[Any] = []

        if action is not None:
            conditions.append("al.action = %s")
            parameters.append(action)

        if start_time is not None:
            conditions.append("al.created_at >= %s")
            parameters.append(start_time)

        if end_time is not None:
            conditions.append("al.created_at < %s")
            parameters.append(end_time)

        where_clause = (
            "WHERE " + " AND ".join(conditions)
            if conditions
            else ""
        )

        query = f"""
            SELECT
                al.id,
                al.user_id,
                u.username,
                u.full_name,
                al.booking_id,
                al.action,
                al.details,
                al.created_at
            FROM audit_log AS al
            LEFT JOIN users AS u
                ON u.id = al.user_id
            {where_clause}
            ORDER BY al.created_at DESC, al.id DESC
            LIMIT %s
            OFFSET %s;
        """

        parameters.extend((limit, offset))

        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(query, parameters)
                rows = cursor.fetchall()

        return [dict(row) for row in rows]
