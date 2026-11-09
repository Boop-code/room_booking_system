import logging
import socket
from typing import Any

from server.handlers.request_handler import handle_request
from shared.protocol import (
    MAX_MESSAGE_SIZE,
    ProtocolError,
    parse_request,
    create_error_response,
    encode_message,
)


logger = logging.getLogger(__name__)


def _send_response(
    client_socket: socket.socket,
    response: dict[str, Any],
) -> None:
    """Отправляет JSON-ответ клиенту."""

    client_socket.sendall(encode_message(response))


def handle_client(
    client_socket: socket.socket,
    client_address: tuple[str, int],
) -> None:
    """Обрабатывает запросы одного TCP-клиента."""

    logger.info("Подключён клиент %s:%s", *client_address)

    request_id = None

    try:
        client_socket.settimeout(300)

        with client_socket:
            with client_socket.makefile(
                "r",
                encoding="utf-8",
                newline="\n",
            ) as reader:

                while True:
                    message = reader.readline(MAX_MESSAGE_SIZE + 1)

                    if not message:
                        break

                    if len(message.encode("utf-8")) > MAX_MESSAGE_SIZE:
                        _send_response(
                            client_socket,
                            create_error_response(
                                None,
                                "Размер сообщения превышает допустимый предел.",
                                "MESSAGE_TOO_LARGE",
                            ),
                        )
                        break

                    try:
                        request = parse_request(message)
                        request_id = request["request_id"]

                        response = handle_request(request)

                    except ProtocolError as error:
                        response = create_error_response(
                            request_id,
                            str(error),
                            "INVALID_REQUEST",
                        )

                    except Exception:
                        logger.exception(
                            "Ошибка обработки запроса клиента %s:%s",
                            *client_address,
                        )
                        response = create_error_response(
                            request_id,
                            "Внутренняя ошибка сервера.",
                            "INTERNAL_ERROR",
                        )

                    _send_response(client_socket, response)

    except (ConnectionError, OSError, UnicodeDecodeError):
        logger.warning(
            "Соединение с клиентом %s:%s прервано.",
            *client_address,
        )

    finally:
        logger.info(
            "Клиент %s:%s отключён.",
            *client_address,
        )
