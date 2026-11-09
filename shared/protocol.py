import json
from typing import Any


MAX_MESSAGE_SIZE = 1024 * 1024


class ProtocolError(Exception):
    """Ошибка формата сетевого сообщения."""


def parse_request(message: str) -> dict[str, Any]:
    """Преобразует JSON-строку в проверенный запрос."""

    try:
        request = json.loads(message)
    except json.JSONDecodeError as error:
        raise ProtocolError("Некорректный формат JSON.") from error

    if not isinstance(request, dict):
        raise ProtocolError("Запрос должен быть JSON-объектом.")

    action = request.get("action")

    if not isinstance(action, str) or not action.strip():
        raise ProtocolError("Не указано действие (action).")

    request_id = request.get("request_id")

    if request_id is not None and not isinstance(
        request_id, (str, int)
    ):
        raise ProtocolError("Некорректный request_id.")

    data = request.get("data", {})

    if not isinstance(data, dict):
        raise ProtocolError("Поле data должно быть JSON-объектом.")

    return {
        "request_id": request_id,
        "action": action.strip(),
        "data": data,
    }


def create_response(
    request_id: str | int | None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Создаёт успешный ответ сервера."""

    return {
        "request_id": request_id,
        "success": True,
        "data": data or {},
        "error": None,
    }


def create_error_response(
    request_id: str | int | None,
    message: str,
    code: str = "REQUEST_ERROR",
) -> dict[str, Any]:
    """Создаёт ответ с ошибкой."""

    return {
        "request_id": request_id,
        "success": False,
        "data": {},
        "error": {
            "code": code,
            "message": message,
        },
    }


def encode_message(response: dict[str, Any]) -> bytes:
    """Кодирует ответ в JSON и добавляет символ конца строки."""

    return (
        json.dumps(response, ensure_ascii=False) + "\n"
    ).encode("utf-8")
