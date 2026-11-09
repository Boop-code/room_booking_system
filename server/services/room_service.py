from typing import Any

from server.repositories.room_repository import RoomRepository


class RoomService:
    """Сервис получения и фильтрации помещений."""

    def __init__(
        self,
        repository: RoomRepository | None = None,
    ) -> None:
        self.repository = repository or RoomRepository()

    def get_rooms(
        self,
        category_id: int | None = None,
        min_capacity: int | None = None,
        is_active: bool = True,
    ) -> list[dict[str, Any]]:
        """Возвращает помещения с проверкой фильтров."""

        if category_id is not None:
            if (
                isinstance(category_id, bool)
                or not isinstance(category_id, int)
                or category_id <= 0
            ):
                raise ValueError(
                    "Идентификатор категории должен быть положительным целым числом."
                )

        if min_capacity is not None:
            if (
                isinstance(min_capacity, bool)
                or not isinstance(min_capacity, int)
                or min_capacity <= 0
            ):
                raise ValueError(
                    "Минимальная вместимость должна быть положительным целым числом."
                )

        if not isinstance(is_active, bool):
            raise ValueError(
                "Параметр is_active должен иметь логическое значение."
            )

        return self.repository.get_all(
            category_id=category_id,
            min_capacity=min_capacity,
            is_active=is_active,
        )
