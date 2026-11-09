import json
import socket
from typing import Any


HOST = "127.0.0.1"
PORT = 5050


def send_request(
    reader: Any,
    client: socket.socket,
    request_id: str,
    action: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Отправляет запрос серверу и получает JSON-ответ."""

    request = {
        "request_id": request_id,
        "action": action,
        "data": data or {},
    }

    message = json.dumps(request, ensure_ascii=False) + "\n"
    client.sendall(message.encode("utf-8"))

    response_line = reader.readline()

    if not response_line:
        raise ConnectionError("Сервер закрыл соединение.")

    return json.loads(response_line)


def main() -> None:
    """Проверяет команды каталога помещений."""

    with socket.create_connection((HOST, PORT), timeout=5) as client:
        with client.makefile(
            "r",
            encoding="utf-8",
            newline="\n",
        ) as reader:

            # Проверка получения категорий.
            categories_response = send_request(
                reader,
                client,
                "catalog-1",
                "list_categories",
            )

            print("Категории:")
            print(
                json.dumps(
                    categories_response,
                    ensure_ascii=False,
                    indent=4,
                )
            )

            assert categories_response["success"] is True

            categories = categories_response["data"]["categories"]
            assert len(categories) == 4

            category_id = categories[0]["id"]

            # Проверка получения всех активных помещений.
            rooms_response = send_request(
                reader,
                client,
                "catalog-2",
                "list_rooms",
            )

            print("\nВсе активные помещения:")
            print(
                json.dumps(
                    rooms_response,
                    ensure_ascii=False,
                    indent=4,
                )
            )

            assert rooms_response["success"] is True

            # Проверка фильтрации.
            filtered_response = send_request(
                reader,
                client,
                "catalog-3",
                "list_rooms",
                {
                    "category_id": category_id,
                    "min_capacity": 10,
                },
            )

            print("\nРезультат фильтрации:")
            print(
                json.dumps(
                    filtered_response,
                    ensure_ascii=False,
                    indent=4,
                )
            )

            assert filtered_response["success"] is True

            for room in filtered_response["data"]["rooms"]:
                assert room["category_id"] == category_id
                assert room["capacity"] >= 10
                assert room["is_active"] is True

            # Проверка некорректного фильтра.
            invalid_response = send_request(
                reader,
                client,
                "catalog-4",
                "list_rooms",
                {"min_capacity": -5},
            )

            print("\nПроверка некорректного фильтра:")
            print(
                json.dumps(
                    invalid_response,
                    ensure_ascii=False,
                    indent=4,
                )
            )

            assert invalid_response["success"] is False
            assert invalid_response["error"]["code"] == "INVALID_DATA"

    print("\nВсе проверки каталога пройдены!")


if __name__ == "__main__":
    main()
