from datetime import datetime, timezone
from typing import Any

from psycopg.errors import ExclusionViolation

from server.repositories.booking_repository import BookingRepository


class BookingError(Exception):
    """Ошибка при выполнении операции бронирования."""


class BookingService:
    """Бизнес-логика бронирования помещений."""

    def __init__(
        self,
        booking_repository: BookingRepository | None = None,
    ) -> None:
        self._repository = booking_repository or BookingRepository()

    @staticmethod
    def _validate_id(value: Any, field_name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise BookingError(
                f"Поле «{field_name}» должно быть положительным целым числом."
            )
        return value

    @staticmethod
    def _validate_datetime(value: Any, field_name: str) -> datetime:
        if not isinstance(value, datetime):
            raise BookingError(
                f"Поле «{field_name}» должно содержать дату и время."
            )

        if value.tzinfo is None or value.utcoffset() is None:
            raise BookingError(
                f"Поле «{field_name}» должно содержать часовой пояс."
            )

        return value

    def create_booking(
        self,
        room_id: Any,
        user_id: Any,
        start_time: Any,
        end_time: Any,
        purpose: Any,
    ) -> dict[str, Any]:
        """Проверяет данные и создаёт бронирование."""

        room_id = self._validate_id(room_id, "room_id")
        user_id = self._validate_id(user_id, "user_id")

        start_time = self._validate_datetime(start_time, "start_time")
        end_time = self._validate_datetime(end_time, "end_time")

        if end_time <= start_time:
            raise BookingError(
                "Время окончания должно быть позже времени начала."
            )

        if start_time <= datetime.now(timezone.utc):
            raise BookingError(
                "Нельзя создать бронирование на прошедшее время."
            )

        if not isinstance(purpose, str):
            raise BookingError("Цель бронирования должна быть строкой.")

        purpose = purpose.strip()

        if not purpose:
            raise BookingError("Укажите цель бронирования.")

        if len(purpose) > 500:
            raise BookingError(
                "Цель бронирования не должна превышать 500 символов."
            )

        room = self._repository.get_room_for_booking(room_id)

        if room is None:
            raise BookingError("Указанное помещение не найдено.")

        if not room["is_active"]:
            raise BookingError("Это помещение сейчас недоступно.")

        if not self._repository.user_exists(user_id):
            raise BookingError("Указанный пользователь не найден.")

        try:
            return self._repository.create(
                room_id=room_id,
                user_id=user_id,
                start_time=start_time,
                end_time=end_time,
                purpose=purpose,
            )
        except ExclusionViolation as error:
            raise BookingError(
                "Помещение уже забронировано на выбранное время."
            ) from error

    def get_booking(self, booking_id: Any) -> dict[str, Any] | None:
        booking_id = self._validate_id(booking_id, "booking_id")
        return self._repository.get_by_id(booking_id)


    def cancel_booking(
        self,
        booking_id: Any,
        user_id: Any,
    ) -> dict[str, Any]:
        """Отменяет активное бронирование текущего пользователя."""
        booking_id = self._validate_id(booking_id, "booking_id")
        user_id = self._validate_id(user_id, "user_id")

        booking = self._repository.cancel(
            booking_id=booking_id,
            user_id=user_id,
        )

        if booking is None:
            raise BookingError(
                "Активное бронирование не найдено или принадлежит другому пользователю."
            )

        return booking


    def get_user_bookings(
        self,
        user_id: Any,
        include_cancelled: bool = False,
    ) -> list[dict[str, Any]]:
        user_id = self._validate_id(user_id, "user_id")

        if not isinstance(include_cancelled, bool):
            raise BookingError(
                "Параметр include_cancelled должен быть логическим."
            )

        return self._repository.get_user_bookings(
            user_id=user_id,
            include_cancelled=include_cancelled,
        )

    def get_room_schedule(
        self,
        room_id: Any,
        start_time: Any,
        end_time: Any,
        include_cancelled: bool = False,
    ) -> list[dict[str, Any]]:
        room_id = self._validate_id(room_id, "room_id")
        start_time = self._validate_datetime(start_time, "start_time")
        end_time = self._validate_datetime(end_time, "end_time")

        if end_time <= start_time:
            raise BookingError(
                "Время окончания интервала должно быть позже начала."
            )

        if not isinstance(include_cancelled, bool):
            raise BookingError(
                "Параметр include_cancelled должен быть логическим."
            )

        return self._repository.get_room_schedule(
            room_id=room_id,
            start_time=start_time,
            end_time=end_time,
            include_cancelled=include_cancelled,
        )
