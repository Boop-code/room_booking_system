
import json
import socket
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


HOST = "127.0.0.1"
PORT = 5050

TOKEN_FILE = Path(__file__).resolve().parent.parent / "admin_token.txt"


def load_admin_token():
    """Загружает токен администратора."""

    if not TOKEN_FILE.exists():
        raise FileNotFoundError(
            "Файл admin_token.txt не найден. "
            "Сначала выполни вход под администратором."
        )

    token = TOKEN_FILE.read_text(encoding="utf-8").strip()

    if not token:
        raise ValueError("Файл admin_token.txt пуст.")

    return token


def send_request(action, data=None, token=None):
    """Отправляет запрос серверу и получает JSON-ответ."""

    request_data = dict(data or {})

    if token is not None:
        request_data["token"] = token

    request = {
        "request_id": str(uuid.uuid4()),
        "action": action,
        "data": request_data,
    }

    with socket.create_connection((HOST, PORT), timeout=5) as client:
        client.settimeout(10)

        client.sendall(
            (json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8")
        )

        with client.makefile("r", encoding="utf-8") as reader:
            response_line = reader.readline()

    if not response_line:
        raise RuntimeError("Сервер не вернул ответ.")

    return json.loads(response_line)


def check(condition, message):
    if not condition:
        raise AssertionError(message)

    print(f"[OK] {message}")


def get_error_code(response):
    """Извлекает код ошибки из ответа сервера."""

    error = response.get("error", {})

    if isinstance(error, dict):
        return error.get("code")

    return response.get("error_code")


def main():
    print("Проверка статистики системы бронирования\n")

    token = load_admin_token()
    print("Токен администратора загружен.\n")

    start_time = (
        datetime.now(timezone.utc) - timedelta(days=30)
    ).replace(second=0, microsecond=0)

    end_time = (
        datetime.now(timezone.utc) + timedelta(days=30)
    ).replace(second=0, microsecond=0)

    search_data = {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }

    # 1. Получение общей статистики.
    print("1. Получение общей статистики")

    response = send_request(
        "get_statistics",
        search_data,
        token,
    )

    if response.get("success") is not True:
        raise RuntimeError(
            "Не удалось получить статистику:\n"
            + json.dumps(response, ensure_ascii=False, indent=4)
        )

    check(
        response.get("success") is True,
        "Запрос статистики выполнен успешно",
    )

    statistics = response.get("data", {})

    check(
        isinstance(statistics, dict),
        "Получен объект статистики",
    )

    check(
        "period" in statistics,
        "В ответе присутствует временной период",
    )

    check(
        statistics.get("period", {}).get("start_time") == start_time.isoformat(),
        "Начало периода соответствует запросу",
    )

    check(
        statistics.get("period", {}).get("end_time") == end_time.isoformat(),
        "Окончание периода соответствует запросу",
    )

    # 2. Проверка загрузки помещений.
    print("\n2. Проверка загрузки помещений")

    occupancy = statistics.get("room_occupancy")

    check(
        isinstance(occupancy, list),
        "Получен список загрузки помещений",
    )

    check(
        len(occupancy) > 0,
        "В статистике присутствуют помещения",
    )

    required_occupancy_fields = {
        "room_id",
        "room_name",
        "room_number",
        "category_name",
        "capacity",
        "booking_count",
        "booked_hours",
        "occupancy_percent",
    }

    check(
        required_occupancy_fields.issubset(occupancy[0].keys()),
        "Данные загрузки содержат все необходимые показатели",
    )

    check(
        all(
            0 <= float(room["occupancy_percent"]) <= 100
            for room in occupancy
        ),
        "Процент загрузки находится в диапазоне от 0 до 100",
    )

    check(
        all(
            float(room["booked_hours"]) >= 0
            for room in occupancy
        ),
        "Количество занятых часов неотрицательное",
    )

    check(
        all(
            int(room["booking_count"]) > 0
            or (
                float(room["booked_hours"]) == 0
                and float(room["occupancy_percent"]) == 0
            )
            for room in occupancy
        ),
        "Помещения без бронирований имеют нулевую загрузку",
    )

    # 3. Проверка количества бронирований по категориям.
    print("\n3. Проверка бронирований по категориям")

    categories = statistics.get("bookings_by_category")

    check(
        isinstance(categories, list),
        "Получен список статистики по категориям",
    )

    check(
        len(categories) >= 4,
        "В статистике присутствуют все четыре категории помещений",
    )

    required_category_fields = {
        "category_id",
        "category_name",
        "active_bookings",
        "cancelled_bookings",
        "total_bookings",
    }

    check(
        required_category_fields.issubset(categories[0].keys()),
        "Данные категорий содержат необходимые показатели",
    )

    check(
        all(
            category["total_bookings"]
            == category["active_bookings"] + category["cancelled_bookings"]
            for category in categories
        ),
        "Общее количество бронирований соответствует сумме активных и отменённых",
    )

    # 4. Проверка популярных часов.
    print("\n4. Проверка популярных часов")

    popular_hours = statistics.get("popular_hours")

    check(
        isinstance(popular_hours, list),
        "Получен список популярных часов",
    )

    required_hour_fields = {
        "hour",
        "booking_count",
    }

    if popular_hours:
        check(
            required_hour_fields.issubset(popular_hours[0].keys()),
            "Данные популярных часов содержат необходимые показатели",
        )

        check(
            all(
                0 <= item["hour"] <= 23
                and item["booking_count"] > 0
                for item in popular_hours
            ),
            "Значения часов и количества бронирований корректны",
        )
    else:
        print(
            "[INFO] За выбранный период активных бронирований не найдено."
        )

    # 5. Проверка некорректного временного периода.
    print("\n5. Проверка некорректного временного периода")

    invalid_response = send_request(
        "get_statistics",
        {
            "start_time": end_time.isoformat(),
            "end_time": start_time.isoformat(),
        },
        token,
    )

    check(
        invalid_response.get("success") is False,
        "Некорректный период отклонён сервером",
    )

    check(
        get_error_code(invalid_response) == "INVALID_DATA",
        "Возвращён код INVALID_DATA",
    )

    # 6. Проверка отсутствия часового пояса.
    print("\n6. Проверка отсутствия часового пояса")

    no_timezone_response = send_request(
        "get_statistics",
        {
            "start_time": "2026-11-01T10:00:00",
            "end_time": "2026-11-30T10:00:00",
        },
        token,
    )

    check(
        no_timezone_response.get("success") is False,
        "Дата без часового пояса отклонена",
    )

    check(
        get_error_code(no_timezone_response) == "INVALID_DATA",
        "Возвращён код INVALID_DATA",
    )

    print("\nВсе проверки статистики пройдены!")


if __name__ == "__main__":
    main()
