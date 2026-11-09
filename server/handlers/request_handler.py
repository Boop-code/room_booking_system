import logging
from typing import Any

from server.database.connection import get_connection
from server.services.category_service import CategoryService
from server.services.room_service import RoomService
from shared.protocol import (
    create_response,
    create_error_response,
)


logger = logging.getLogger(__name__)


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    """Обрабатывает запрос клиента и возвращает ответ."""

    request_id = request.get("request_id")
    action = request["action"]
    data = request["data"]

    if action == "ping":
        return create_response(
            request_id,
            {
                "message": "Сервер работает.",
                "status": "pong",
            },
        )

    if action == "health":
        try:
            with get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            current_database(),
                            current_timestamp;
                        """
                    )
                    database_name, server_time = cursor.fetchone()

            return create_response(
                request_id,
                {
                    "status": "ok",
                    "database": database_name,
                    "server_time": server_time.isoformat(),
                },
            )

        except Exception:
            logger.exception("Ошибка проверки базы данных.")
            return create_error_response(
                request_id,
                "Не удалось проверить подключение к базе данных.",
                "DATABASE_ERROR",
            )

    if action == "list_categories":
        try:
            categories = CategoryService().get_categories()

            return create_response(
                request_id,
                {
                    "categories": categories,
                    "count": len(categories),
                },
            )

        except Exception:
            logger.exception("Ошибка получения категорий.")
            return create_error_response(
                request_id,
                "Не удалось получить список категорий.",
                "DATABASE_ERROR",
            )

    if action == "list_rooms":
        try:
            rooms = RoomService().get_rooms(
                category_id=data.get("category_id"),
                min_capacity=data.get("min_capacity"),
                is_active=data.get("is_active", True),
            )

            return create_response(
                request_id,
                {
                    "rooms": rooms,
                    "count": len(rooms),
                },
            )

        except ValueError as error:
            return create_error_response(
                request_id,
                str(error),
                "INVALID_DATA",
            )

        except Exception:
            logger.exception("Ошибка получения помещений.")
            return create_error_response(
                request_id,
                "Не удалось получить список помещений.",
                "DATABASE_ERROR",
            )

    return create_error_response(
        request_id,
        f"Неизвестное действие: {action}",
        "UNKNOWN_ACTION",
    )
