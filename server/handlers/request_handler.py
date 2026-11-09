from typing import Any

from server.database.connection import get_connection
from shared.protocol import (
    ProtocolError,
    create_response,
    create_error_response,
)


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    """Обрабатывает запрос клиента и возвращает ответ."""

    request_id = request.get("request_id")
    action = request["action"]

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
            raise

    return create_error_response(
        request_id,
        f"Неизвестное действие: {action}",
        "UNKNOWN_ACTION",
    )
