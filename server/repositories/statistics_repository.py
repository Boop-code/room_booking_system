
from datetime import datetime
from typing import Any

from psycopg.rows import dict_row

from server.database.connection import get_connection


class StatisticsRepository:
    """Репозиторий для получения статистики бронирований."""

    def get_room_occupancy(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        """Возвращает загрузку каждого активного помещения за период."""

        query = """
            WITH period AS (
                SELECT
                    %s::timestamptz AS start_time,
                    %s::timestamptz AS end_time
            )
            SELECT
                r.id AS room_id,
                r.name AS room_name,
                r.room_number,
                c.name AS category_name,
                r.capacity,
                COUNT(b.id) AS booking_count,
                ROUND(
                    (
                        COALESCE(
                            SUM(
                                EXTRACT(
                                    EPOCH FROM (
                                        LEAST(b.end_time, p.end_time)
                                        - GREATEST(b.start_time, p.start_time)
                                    )
                                ) / 3600
                            ) FILTER (WHERE b.id IS NOT NULL),
                            0
                        )
                    )::numeric,
                    2
                ) AS booked_hours,
                ROUND(
                    (
                        COALESCE(
                            SUM(
                                EXTRACT(
                                    EPOCH FROM (
                                        LEAST(b.end_time, p.end_time)
                                        - GREATEST(b.start_time, p.start_time)
                                    )
                                )
                            ) FILTER (WHERE b.id IS NOT NULL),
                            0
                        )
                        / EXTRACT(
                            EPOCH FROM (p.end_time - p.start_time)
                        ) * 100
                    )::numeric,
                    2
                ) AS occupancy_percent
            FROM rooms r
            JOIN categories c ON c.id = r.category_id
            CROSS JOIN period p
            LEFT JOIN bookings b
                ON b.room_id = r.id
                AND b.status = 'active'
                AND b.start_time < p.end_time
                AND b.end_time > p.start_time
            WHERE r.is_active = TRUE
            GROUP BY
                r.id,
                r.name,
                r.room_number,
                c.name,
                r.capacity,
                p.start_time,
                p.end_time
            ORDER BY occupancy_percent DESC, r.room_number;
        """

        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(query, (start_time, end_time))
                rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def get_bookings_by_category(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        """Возвращает количество бронирований по категориям."""

        query = """
            SELECT
                c.id AS category_id,
                c.name AS category_name,
                COUNT(b.id) FILTER (
                    WHERE b.status = 'active'
                ) AS active_bookings,
                COUNT(b.id) FILTER (
                    WHERE b.status = 'cancelled'
                ) AS cancelled_bookings,
                COUNT(b.id) AS total_bookings
            FROM categories c
            LEFT JOIN rooms r ON r.category_id = c.id
            LEFT JOIN bookings b
                ON b.room_id = r.id
                AND b.start_time < %s
                AND b.end_time > %s
            GROUP BY c.id, c.name
            ORDER BY total_bookings DESC, c.name;
        """

        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(query, (end_time, start_time))
                rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def get_popular_hours(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        """Возвращает популярные часы начала бронирований."""

        query = """
            SELECT
                EXTRACT(HOUR FROM b.start_time)::integer AS hour,
                COUNT(*) AS booking_count
            FROM bookings b
            WHERE b.status = 'active'
                AND b.start_time >= %s
                AND b.start_time < %s
            GROUP BY EXTRACT(HOUR FROM b.start_time)
            ORDER BY booking_count DESC, hour ASC;
        """

        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(query, (start_time, end_time))
                rows = cursor.fetchall()

        return [dict(row) for row in rows]
