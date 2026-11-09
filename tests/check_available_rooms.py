import json
import socket
import uuid
from datetime import datetime, timedelta, timezone


HOST = "127.0.0.1"
PORT = 5050


def send_request(action: str, data: dict | None = None) -> dict:
    request = {
        "request_id": str(uuid.uuid4()),
        "action": action,
        "data": data or {},
    }

    with socket.create_connection((HOST, PORT), timeout=5) as client:
        client.sendall(
            (json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8")
        )

        with client.makefile("r", encoding="utf-8") as reader:
            response_line = reader.readline()

    if not response_line:
        raise RuntimeError("Сервер не вернул ответ.")

    return json.loads(response_line)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)

    print(f"[OK] {message}")


def main() -> None:
    print("Проверка поиска свободных помещений\n")

    start_time = (
        datetime.now(timezone.utc) + timedelta(days=60)
    ).replace(second=0, microsecond=0)

    end_time = start_time + timedelta(hours=2)

    search_data = {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }

    print("1. Поиск всех свободных помещений")

    result = send_request("find_available_rooms", search_data)

    check(result["success"], "Поиск выполнен успешно")

    rooms = result["data"]["rooms"]

    check(
        result["data"]["count"] == len(rooms),
        "Количество результатов соответствует списку",
    )

    check(
        all(room["is_active"] for room in rooms),
        "В результатах присутствуют только активные помещения",
    )

    print("\n2. Фильтрация по категории")

    result = send_request(
        "find_available_rooms",
        {
            **search_data,
            "category_id": 2,
        },
    )

    check(result["success"], "Фильтрация по категории выполнена")

    check(
        all(room["category_id"] == 2 for room in result["data"]["rooms"]),
        "Все найденные помещения принадлежат категории 2",
    )

    print("\n3. Фильтрация по вместимости")

    result = send_request(
        "find_available_rooms",
        {
            **search_data,
            "min_capacity": 25,
        },
    )

    check(result["success"], "Фильтрация по вместимости выполнена")

    check(
        all(room["capacity"] >= 25 for room in result["data"]["rooms"]),
        "Все помещения имеют вместимость не менее 25 человек",
    )

    print("\n4. Совместная фильтрация")

    result = send_request(
        "find_available_rooms",
        {
            **search_data,
            "category_id": 1,
            "min_capacity": 25,
        },
    )

    check(result["success"], "Совместная фильтрация выполнена")

    check(
        all(
            room["category_id"] == 1 and room["capacity"] >= 25
            for room in result["data"]["rooms"]
        ),
        "Результаты соответствуют обоим фильтрам",
    )

    print("\n5. Проверка некорректного интервала")

    result = send_request(
        "find_available_rooms",
        {
            "start_time": end_time.isoformat(),
            "end_time": start_time.isoformat(),
        },
    )

    check(
        not result["success"]
        and result["error"]["code"] == "INVALID_DATA",
        "Некорректный временной интервал отклонён",
    )

    print("\n6. Проверка отсутствия часового пояса")

    result = send_request(
        "find_available_rooms",
        {
            "start_time": start_time.replace(tzinfo=None).isoformat(),
            "end_time": end_time.isoformat(),
        },
    )

    check(
        not result["success"]
        and result["error"]["code"] == "INVALID_DATA",
        "Дата без часового пояса отклонена",
    )

    print("\nВсе проверки поиска свободных помещений пройдены!")


if __name__ == "__main__":
    main()
