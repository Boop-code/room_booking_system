from datetime import datetime
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from server.database.connection import get_connection


class BookingRepository:
    """Репозиторий для работы с бронированиями помещений."""

    def get_room_for_booking(self, room_id: int) -> dict[str, Any] | None:
        """Возвращает основные сведения о помещении."""
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT id, name, room_number, is_active
                    FROM rooms
                    WHERE id = %s;
                    """,
                    (room_id,),
                )
                room = cursor.fetchone()

        return dict(room) if room else None

    def user_exists(self, user_id: int) -> bool:
        """Проверяет существование пользователя."""
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT EXISTS(SELECT 1 FROM users WHERE id = %s);",
                    (user_id,),
                )
                result = cursor.fetchone()

        return bool(result[0])

    def create(
        self,
        room_id: int,
        user_id: int,
        start_time: datetime,
        end_time: datetime,
        purpose: str,
    ) -> dict[str, Any]:
        """Создаёт бронирование и записывает событие в журнал аудита."""
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    INSERT INTO bookings (
                        room_id,
                        user_id,
                        start_time,
                        end_time,
                        purpose,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s, 'active')
                    RETURNING
                        id,
                        room_id,
                        user_id,
                        start_time,
                        end_time,
                        purpose,
                        status,
                        created_at;
                    """,
                    (room_id, user_id, start_time, end_time, purpose),
                )
                booking = dict(cursor.fetchone())

                cursor.execute(
                    """
                    INSERT INTO audit_log (
                        user_id,
                        booking_id,
                        action,
                        details
                    )
                    VALUES (%s, %s, %s, %s);
                    """,
                    (
                        user_id,
                        booking["id"],
                        "booking_created",
                        Jsonb({
                            "room_id": room_id,
                            "start_time": start_time.isoformat(),
                            "end_time": end_time.isoformat(),
                            "purpose": purpose,
                        }),
                    ),
                )

        return booking

    def get_by_id(self, booking_id: int) -> dict[str, Any] | None:
        """Возвращает бронирование по идентификатору."""
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT
                        b.id,
                        b.room_id,
                        r.name AS room_name,
                        r.room_number,
                        b.user_id,
                        u.username,
                        u.full_name,
                        b.start_time,
                        b.end_time,
                        b.purpose,
                        b.status,
                        b.created_at,
                        b.cancelled_at
                    FROM bookings AS b
                    JOIN rooms AS r ON r.id = b.room_id
                    JOIN users AS u ON u.id = b.user_id
                    WHERE b.id = %s;
                    """,
                    (booking_id,),
                )
                booking = cursor.fetchone()

        return dict(booking) if booking else None

    def get_user_bookings(
        self,
        user_id: int,
        include_cancelled: bool = False,
    ) -> list[dict[str, Any]]:
        """Возвращает бронирования пользователя."""
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT
                        b.id,
                        b.room_id,
                        r.name AS room_name,
                        r.room_number,
                        c.name AS category_name,
                        b.start_time,
                        b.end_time,
                        b.purpose,
                        b.status,
                        b.created_at,
                        b.cancelled_at
                    FROM bookings AS b
                    JOIN rooms AS r ON r.id = b.room_id
                    JOIN categories AS c ON c.id = r.category_id
                    WHERE b.user_id = %s
                      AND (%s OR b.status = 'active')
                    ORDER BY b.start_time DESC, b.id DESC;
                    """,
                    (user_id, include_cancelled),
                )
                bookings = cursor.fetchall()

        return [dict(booking) for booking in bookings]

    def get_room_schedule(
        self,
        room_id: int,
        start_time: datetime,
        end_time: datetime,
        include_cancelled: bool = False,
    ) -> list[dict[str, Any]]:
        """Возвращает бронирования помещения за заданный интервал."""
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT
                        b.id,
                        b.room_id,
                        b.user_id,
                        u.full_name,
                        b.start_time,
                        b.end_time,
                        b.purpose,
                        b.status
                    FROM bookings AS b
                    JOIN users AS u ON u.id = b.user_id
                    WHERE b.room_id = %s
                      AND b.start_time < %s
                      AND b.end_time > %s
                      AND (%s OR b.status = 'active')
                    ORDER BY b.start_time, b.id;
                    """,
                    (
                        room_id,
                        end_time,
                        start_time,
                        include_cancelled,
                    ),
                )
                bookings = cursor.fetchall()

        return [dict(booking) for booking in bookings]

    def cancel(
        self,
        booking_id: int,
        user_id: int,
    ) -> dict[str, Any] | None:
        """
        Отменяет активное бронирование пользователя
        и записывает событие в журнал аудита.

        None означает, что активное бронирование пользователя не найдено.
        """
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    UPDATE bookings
                    SET
                        status = 'cancelled',
                        cancelled_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                      AND user_id = %s
                      AND status = 'active'
                    RETURNING
                        id,
                        room_id,
                        user_id,
                        start_time,
                        end_time,
                        purpose,
                        status,
                        created_at,
                        cancelled_at;
                    """,
                    (booking_id, user_id),
                )
                booking = cursor.fetchone()

                if booking is None:
                    return None

                booking = dict(booking)

                cursor.execute(
                    """
                    INSERT INTO audit_log (
                        user_id,
                        booking_id,
                        action,
                        details
                    )
                    VALUES (%s, %s, %s, %s);
                    """,
                    (
                        user_id,
                        booking_id,
                        "booking_cancelled",
                        Jsonb({
                            "room_id": booking["room_id"],
                            "start_time": booking["start_time"].isoformat(),
                            "end_time": booking["end_time"].isoformat(),
                            "purpose": booking["purpose"],
                        }),
                    ),
                )

        return booking
