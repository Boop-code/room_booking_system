from datetime import datetime, timezone
from typing import Any

from server.repositories.room_repository import RoomRepository


class RoomService:
    """Сервис получения, фильтрации и поиска помещений."""

    def __init__(
        self,
        repository: RoomRepository | None = None,
    ) -> None:
        self.repository = repository or RoomRepository()

    @staticmethod
    def _validate_filters(
        category_id: Any,
        min_capacity: Any,
        is_active: Any,
    ) -> None:
        if category_id is not None:
            if (
                isinstance(category_id, bool)
                or not isinstance(category_id, int)
                or category_id <= 0
            ):
                raise ValueError(
                    "Идентификатор категории должен быть "
                    "положительным целым числом."
                )

        if min_capacity is not None:
            if (
                isinstance(min_capacity, bool)
                or not isinstance(min_capacity, int)
                or min_capacity <= 0
            ):
                raise ValueError(
                    "Минимальная вместимость должна быть "
                    "положительным целым числом."
                )

        if not isinstance(is_active, bool):
            raise ValueError(
                "Параметр is_active должен иметь логическое значение."
            )

    @staticmethod
    def _validate_datetime(value: Any, field_name: str) -> None:
        if not isinstance(value, datetime):
            raise ValueError(
                f"Поле {field_name} должно содержать дату и время."
            )

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                f"Поле {field_name} должно содержать часовой пояс."
            )

    def get_rooms(
        self,
        category_id: int | None = None,
        min_capacity: int | None = None,
        is_active: bool = True,
    ) -> list[dict[str, Any]]:
        """Возвращает помещения с проверкой фильтров."""

        self._validate_filters(
            category_id,
            min_capacity,
            is_active,
        )

        return self.repository.get_all(
            category_id=category_id,
            min_capacity=min_capacity,
            is_active=is_active,
        )

    def find_available_rooms(
        self,
        start_time: datetime,
        end_time: datetime,
        category_id: int | None = None,
        min_capacity: int | None = None,
    ) -> list[dict[str, Any]]:
        """Ищет свободные помещения на заданный период."""

        self._validate_datetime(start_time, "start_time")
        self._validate_datetime(end_time, "end_time")

        if end_time <= start_time:
            raise ValueError(
                "Время окончания должно быть позже времени начала."
            )

        if start_time <= datetime.now(timezone.utc):
            raise ValueError(
                "Время начала поиска должно быть в будущем."
            )

        self._validate_filters(
            category_id,
            min_capacity,
            True,
        )

        return self.repository.get_available(
            start_time=start_time,
            end_time=end_time,
            category_id=category_id,
            min_capacity=min_capacity,
        )
