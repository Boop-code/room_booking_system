from datetime import datetime
from typing import Any

from psycopg.rows import dict_row

from server.database.connection import get_connection


class RoomRepository:
    """Репозиторий для работы с помещениями."""

    def get_all(
        self,
        category_id: int | None = None,
        min_capacity: int | None = None,
        is_active: bool = True,
    ) -> list[dict[str, Any]]:
        """Возвращает помещения с учётом заданных фильтров."""

        conditions = ["r.is_active = %s"]
        parameters: list[Any] = [is_active]

        if category_id is not None:
            conditions.append("r.category_id = %s")
            parameters.append(category_id)

        if min_capacity is not None:
            conditions.append("r.capacity >= %s")
            parameters.append(min_capacity)

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT
                r.id,
                r.name,
                r.room_number,
                r.category_id,
                c.name AS category_name,
                r.capacity,
                r.description,
                r.is_active
            FROM rooms AS r
            JOIN categories AS c
                ON c.id = r.category_id
            WHERE {where_clause}
            ORDER BY c.name, r.room_number;
        """

        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(query, parameters)
                return [dict(row) for row in cursor.fetchall()]

    def get_available(
        self,
        start_time: datetime,
        end_time: datetime,
        category_id: int | None = None,
        min_capacity: int | None = None,
    ) -> list[dict[str, Any]]:
        """Возвращает свободные помещения на заданный интервал."""

        conditions = [
            "r.is_active = TRUE",
            """
            NOT EXISTS (
                SELECT 1
                FROM bookings AS b
                WHERE b.room_id = r.id
                    AND b.status = 'active'
                    AND b.start_time < %s
                    AND b.end_time > %s
            )
            """,
        ]

        parameters: list[Any] = [end_time, start_time]

        if category_id is not None:
            conditions.append("r.category_id = %s")
            parameters.append(category_id)

        if min_capacity is not None:
            conditions.append("r.capacity >= %s")
            parameters.append(min_capacity)

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT
                r.id,
                r.name,
                r.room_number,
                r.category_id,
                c.name AS category_name,
                r.capacity,
                r.description,
                r.is_active
            FROM rooms AS r
            JOIN categories AS c
                ON c.id = r.category_id
            WHERE {where_clause}
            ORDER BY c.name, r.room_number;
        """

        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(query, parameters)
                return [dict(row) for row in cursor.fetchall()]
