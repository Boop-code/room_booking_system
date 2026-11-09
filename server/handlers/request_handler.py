import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from server.database.connection import get_connection
from server.services.auth_service import AuthService, AuthenticationError
from server.services.booking_service import BookingService, BookingError
from server.services.category_service import CategoryService
from server.services.room_service import RoomService
from shared.protocol import (
    create_response,
    create_error_response,
)

logger = logging.getLogger(__name__)

_auth_service = AuthService()


def _serialize(value: Any) -> Any:
    """Преобразует типы PostgreSQL в значения, совместимые с JSON."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, dict):
        return {
            key: _serialize(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]

    return value


def _parse_datetime(value: Any, field_name: str) -> datetime:
    """Проверяет и разбирает дату и время из ISO 8601."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Поле {field_name} должно содержать дату и время в формате ISO 8601."
        )

    try:
        normalized_value = (
            value[:-1] + "+00:00"
            if value.endswith("Z")
            else value
        )
        result = datetime.fromisoformat(normalized_value)
    except ValueError as error:
        raise ValueError(
            f"Некорректный формат даты и времени в поле {field_name}."
        ) from error

    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(
            f"В поле {field_name} необходимо указать часовой пояс."
        )

    return result


def _get_authenticated_user(data: dict[str, Any]) -> dict[str, Any] | None:
    """Возвращает пользователя по действующему токену."""
    token = data.get("token")

    if not isinstance(token, str) or not token:
        return None

    return _auth_service.sessions.get_user(token)


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    request_id = request.get("request_id")
    action = request["action"]
    data = request["data"]

    if action == "ping":
        return create_response(request_id, {
            "message": "Сервер работает.",
            "status": "pong",
        })

    if action == "health":
        try:
            with get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT current_database(), current_timestamp;
                    """)
                    database_name, server_time = cursor.fetchone()

            return create_response(request_id, {
                "status": "ok",
                "database": database_name,
                "server_time": server_time.isoformat(),
            })
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
            return create_response(request_id, {
                "categories": categories,
                "count": len(categories),
            })
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
            return create_response(request_id, {
                "rooms": rooms,
                "count": len(rooms),
            })
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

    if action == "find_available_rooms":
        try:
            start_time = _parse_datetime(
                data.get("start_time"),
                "start_time",
            )
            end_time = _parse_datetime(
                data.get("end_time"),
                "end_time",
            )

            rooms = RoomService().find_available_rooms(
                start_time=start_time,
                end_time=end_time,
                category_id=data.get("category_id"),
                min_capacity=data.get("min_capacity"),
            )

            return create_response(request_id, {
                "rooms": _serialize(rooms),
                "count": len(rooms),
                "search_period": {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                },
            })

        except ValueError as error:
            return create_error_response(
                request_id,
                str(error),
                "INVALID_DATA",
            )
        except Exception:
            logger.exception("Ошибка поиска свободных помещений.")
            return create_error_response(
                request_id,
                "Не удалось выполнить поиск свободных помещений.",
                "DATABASE_ERROR",
            )

    if action == "login":
        try:
            result = _auth_service.login(
                username=data.get("username"),
                password=data.get("password"),
            )
            return create_response(request_id, result)
        except AuthenticationError as error:
            return create_error_response(
                request_id,
                str(error),
                "AUTH_ERROR",
            )
        except Exception:
            logger.exception("Ошибка авторизации пользователя.")
            return create_error_response(
                request_id,
                "Не удалось выполнить вход.",
                "DATABASE_ERROR",
            )

    if action == "logout":
        try:
            _auth_service.logout(data.get("token"))
            return create_response(request_id, {
                "message": "Выход успешно выполнен.",
            })
        except AuthenticationError as error:
            return create_error_response(
                request_id,
                str(error),
                "AUTH_ERROR",
            )

    # Все операции с бронированиями требуют авторизации.
    if action in {
        "create_booking",
        "my_bookings",
        "room_schedule",
        "cancel_booking",
    }:
        user = _get_authenticated_user(data)

        if user is None:
            return create_error_response(
                request_id,
                "Требуется авторизация. Выполните вход в систему.",
                "AUTH_ERROR",
            )

        booking_service = BookingService()
        user_id = user["user_id"]

        try:
            if action == "create_booking":
                start_time = _parse_datetime(
                    data.get("start_time"),
                    "start_time",
                )
                end_time = _parse_datetime(
                    data.get("end_time"),
                    "end_time",
                )

                booking = booking_service.create_booking(
                    room_id=data.get("room_id"),
                    user_id=user_id,
                    start_time=start_time,
                    end_time=end_time,
                    purpose=data.get("purpose"),
                )

                return create_response(request_id, {
                    "message": "Помещение успешно забронировано.",
                    "booking": _serialize(booking),
                })

            if action == "my_bookings":
                include_cancelled = data.get(
                    "include_cancelled",
                    False,
                )

                bookings = booking_service.get_user_bookings(
                    user_id=user_id,
                    include_cancelled=include_cancelled,
                )

                return create_response(request_id, {
                    "bookings": _serialize(bookings),
                    "count": len(bookings),
                })

            if action == "room_schedule":
                start_time = _parse_datetime(
                    data.get("start_time"),
                    "start_time",
                )
                end_time = _parse_datetime(
                    data.get("end_time"),
                    "end_time",
                )

                bookings = booking_service.get_room_schedule(
                    room_id=data.get("room_id"),
                    start_time=start_time,
                    end_time=end_time,
                    include_cancelled=data.get(
                        "include_cancelled",
                        False,
                    ),
                )

                return create_response(request_id, {
                    "bookings": _serialize(bookings),
                    "count": len(bookings),
                })

            if action == "cancel_booking":
                booking = booking_service.cancel_booking(
                    booking_id=data.get("booking_id"),
                    user_id=user_id,
                )

                return create_response(request_id, {
                    "message": "Бронирование успешно отменено.",
                    "booking": _serialize(booking),
                })

        except ValueError as error:
            return create_error_response(
                request_id,
                str(error),
                "INVALID_DATA",
            )
        except BookingError as error:
            return create_error_response(
                request_id,
                str(error),
                "BOOKING_ERROR",
            )
        except Exception:
            logger.exception(
                "Ошибка выполнения операции бронирования: %s",
                action,
            )
            return create_error_response(
                request_id,
                "Не удалось выполнить операцию бронирования.",
                "DATABASE_ERROR",
            )

    return create_error_response(
        request_id,
        f"Неизвестное действие: {action}",
        "UNKNOWN_ACTION",
    )