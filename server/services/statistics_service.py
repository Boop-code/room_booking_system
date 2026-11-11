from datetime import datetime, timezone
from typing import Any

from server.repositories.statistics_repository import StatisticsRepository


class StatisticsError(Exception):
    """Ошибка при работе со статистикой."""


class StatisticsService:
    """Сервис получения статистики системы бронирования."""

    def __init__(
        self,
        repository: StatisticsRepository | None = None,
    ) -> None:
        self.repository = repository or StatisticsRepository()

    @staticmethod
    def _validate_period(
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        if not isinstance(start_time, datetime):
            raise StatisticsError(
                "Начало периода должно быть датой и временем."
            )

        if not isinstance(end_time, datetime):
            raise StatisticsError(
                "Окончание периода должно быть датой и временем."
            )

        if start_time.tzinfo is None or start_time.utcoffset() is None:
            raise StatisticsError(
                "Начало периода должно содержать часовой пояс."
            )

        if end_time.tzinfo is None or end_time.utcoffset() is None:
            raise StatisticsError(
                "Окончание периода должно содержать часовой пояс."
            )

        if end_time <= start_time:
            raise StatisticsError(
                "Окончание периода должно быть позже его начала."
            )

    def get_room_occupancy(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        self._validate_period(start_time, end_time)

        return self.repository.get_room_occupancy(
            start_time,
            end_time,
        )

    def get_bookings_by_category(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        self._validate_period(start_time, end_time)

        return self.repository.get_bookings_by_category(
            start_time,
            end_time,
        )

    def get_popular_hours(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        self._validate_period(start_time, end_time)

        return self.repository.get_popular_hours(
            start_time,
            end_time,
        )

    def get_full_statistics(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        """Возвращает все основные показатели за один период."""

        self._validate_period(start_time, end_time)

        return {
            "period": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
            "room_occupancy": self.repository.get_room_occupancy(
                start_time,
                end_time,
            ),
            "bookings_by_category": self.repository.get_bookings_by_category(
                start_time,
                end_time,
            ),
            "popular_hours": self.repository.get_popular_hours(
                start_time,
                end_time,
            ),
        }
