from datetime import datetime
from typing import Any

from server.repositories.audit_repository import AuditRepository


class AuditService:
    """Сервис чтения и проверки параметров журнала действий."""

    def __init__(
        self,
        repository: AuditRepository | None = None,
    ) -> None:
        self.repository = repository or AuditRepository()

    @staticmethod
    def _validate_pagination(
        limit: Any,
        offset: Any,
    ) -> tuple[int, int]:
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ValueError("Параметр limit должен быть целым числом.")

        if not 1 <= limit <= 500:
            raise ValueError("Параметр limit должен быть от 1 до 500.")

        if isinstance(offset, bool) or not isinstance(offset, int):
            raise ValueError("Параметр offset должен быть целым числом.")

        if not 0 <= offset <= 1_000_000:
            raise ValueError(
                "Параметр offset должен быть от 0 до 1000000."
            )

        return limit, offset

    @staticmethod
    def _validate_datetime(
        value: Any,
        field_name: str,
    ) -> datetime | None:
        if value is None:
            return None

        if not isinstance(value, datetime):
            raise ValueError(
                f"Поле {field_name} должно содержать дату и время."
            )

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                f"В поле {field_name} необходимо указать часовой пояс."
            )

        return value

    def get_entries(
        self,
        limit: Any = 100,
        offset: Any = 0,
        action: Any = None,
        start_time: Any = None,
        end_time: Any = None,
    ) -> list[dict[str, Any]]:
        """Возвращает записи журнала после проверки параметров."""

        limit, offset = self._validate_pagination(limit, offset)

        if action is not None:
            if not isinstance(action, str):
                raise ValueError("Поле action должно быть строкой.")

            action = action.strip()

            if not action:
                raise ValueError("Поле action не должно быть пустым.")

            if len(action) > 100:
                raise ValueError(
                    "Длина поля action не должна превышать 100 символов."
                )

        start_time = self._validate_datetime(
            start_time,
            "start_time",
        )
        end_time = self._validate_datetime(
            end_time,
            "end_time",
        )

        if (
            start_time is not None
            and end_time is not None
            and end_time <= start_time
        ):
            raise ValueError(
                "Конец периода должен быть позже его начала."
            )

        return self.repository.get_entries(
            limit=limit,
            offset=offset,
            action=action,
            start_time=start_time,
            end_time=end_time,
        )
