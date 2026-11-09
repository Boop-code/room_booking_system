import json
import socket


HOST = "127.0.0.1"
PORT = 5050


def send_request(
    reader,
    client,
    request_id: str,
    action: str,
) -> dict:
    """Отправляет запрос и получает ответ сервера."""

    request = {
        "request_id": request_id,
        "action": action,
        "data": {},
    }

    message = json.dumps(request, ensure_ascii=False) + "\n"
    client.sendall(message.encode("utf-8"))

    response_line = reader.readline()

    if not response_line:
        raise ConnectionError("Сервер закрыл соединение.")

    return json.loads(response_line)


def main() -> None:
    """Проверяет основные команды TCP-сервера."""

    with socket.create_connection((HOST, PORT), timeout=5) as client:
        with client.makefile(
            "r",
            encoding="utf-8",
            newline="\n",
        ) as reader:

            ping = send_request(
                reader,
                client,
                "test-1",
                "ping",
            )
            print("Проверка ping:")
            print(json.dumps(ping, ensure_ascii=False, indent=4))
            assert ping["success"] is True
            assert ping["data"]["status"] == "pong"

            health = send_request(
                reader,
                client,
                "test-2",
                "health",
            )
            print("\nПроверка health:")
            print(json.dumps(health, ensure_ascii=False, indent=4))
            assert health["success"] is True
            assert health["data"]["database"] == "room_booking_db"

            unknown = send_request(
                reader,
                client,
                "test-3",
                "unknown_action",
            )
            print("\nПроверка неизвестной команды:")
            print(json.dumps(unknown, ensure_ascii=False, indent=4))
            assert unknown["success"] is False
            assert unknown["error"]["code"] == "UNKNOWN_ACTION"

    print("\nВсе проверки TCP-сервера пройдены!")


if __name__ == "__main__":
    main()
