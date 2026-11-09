import json
import socket
import uuid
from datetime import datetime, timedelta, timezone

from server.database.connection import (
    close_connection_pool,
    get_connection,
)


HOST = "127.0.0.1"
PORT = 5050

PASSWORD = "TestPassword123"
ROOM_ID = 1


def send_request(action: str, data: dict | None = None) -> dict:
    """Отправляет JSON-запрос TCP-серверу и получает ответ."""
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


def register_and_login(username: str, full_name: str) -> dict:
    registration = send_request("register", {
        "username": username,
        "password": PASSWORD,
        "full_name": full_name,
    })

    check(
        registration["success"],
        f"Пользователь {username} зарегистрирован",
    )

    login = send_request("login", {
        "username": username,
        "password": PASSWORD,
    })

    check(login["success"], f"Пользователь {username} вошёл в систему")

    return login["data"]


def main() -> None:
    print("Проверка системы бронирования\n")

    suffix = uuid.uuid4().hex[:10]
    first_username = f"book_user_{suffix}"
    second_username = f"book_user2_{suffix}"

    first_user = register_and_login(
        first_username,
        "Первый тестовый пользователь",
    )
    second_user = register_and_login(
        second_username,
        "Второй тестовый пользователь",
    )

    first_token = first_user["token"]
    second_token = second_user["token"]

    # Формируем будущий интервал с точностью до минуты.
    start_time = (
        datetime.now(timezone.utc) + timedelta(days=30)
    ).replace(second=0, microsecond=0)

    end_time = start_time + timedelta(hours=1)

    overlapping_start = start_time + timedelta(minutes=30)
    overlapping_end = end_time + timedelta(minutes=30)

    adjacent_end = end_time + timedelta(hours=1)

    start_iso = start_time.isoformat()
    end_iso = end_time.isoformat()

    created_booking_id = None
    adjacent_booking_id = None

    try:
        print("\n1. Создание бронирования")

        created = send_request("create_booking", {
            "token": first_token,
            "room_id": ROOM_ID,
            "start_time": start_iso,
            "end_time": end_iso,
            "purpose": "Проверка системы бронирования",
        })

        check(
            created["success"],
            "Бронирование успешно создано",
        )

        created_booking = created["data"]["booking"]
        created_booking_id = created_booking["id"]

        check(
            created_booking["room_id"] == ROOM_ID,
            "Бронирование связано с правильным помещением",
        )

        print("\n2. Получение списка бронирований")

        my_bookings = send_request("my_bookings", {
            "token": first_token,
        })

        check(my_bookings["success"], "Список бронирований получен")

        check(
            any(
                booking["id"] == created_booking_id
                for booking in my_bookings["data"]["bookings"]
            ),
            "Новое бронирование присутствует в списке пользователя",
        )

        print("\n3. Получение расписания помещения")

        schedule = send_request("room_schedule", {
            "token": first_token,
            "room_id": ROOM_ID,
            "start_time": start_iso,
            "end_time": end_iso,
        })

        check(schedule["success"], "Расписание помещения получено")

        check(
            any(
                booking["id"] == created_booking_id
                for booking in schedule["data"]["bookings"]
            ),
            "Бронирование присутствует в расписании",
        )

        print("\n4. Проверка пересечения интервалов")

        overlapping = send_request("create_booking", {
            "token": second_token,
            "room_id": ROOM_ID,
            "start_time": overlapping_start.isoformat(),
            "end_time": overlapping_end.isoformat(),
            "purpose": "Проверка пересечения",
        })

        check(
            not overlapping["success"]
            and overlapping["error"]["code"] == "BOOKING_ERROR",
            "Пересекающееся бронирование отклонено",
        )

        print("\n5. Проверка смежных интервалов")

        adjacent = send_request("create_booking", {
            "token": second_token,
            "room_id": ROOM_ID,
            "start_time": end_iso,
            "end_time": adjacent_end.isoformat(),
            "purpose": "Проверка смежного интервала",
        })

        check(
            adjacent["success"],
            "Смежное бронирование разрешено",
        )

        adjacent_booking_id = adjacent["data"]["booking"]["id"]

        print("\n6. Проверка защиты от чужой отмены")

        чужая_отмена = send_request("cancel_booking", {
            "token": second_token,
            "booking_id": created_booking_id,
        })

        check(
            not чужая_отмена["success"]
            and чужая_отмена["error"]["code"] == "BOOKING_ERROR",
            "Пользователь не может отменить чужое бронирование",
        )

        print("\n7. Проверка отсутствия доступа без токена")

        без_авторизации = send_request("my_bookings")

        check(
            not без_авторизации["success"]
            and без_авторизации["error"]["code"] == "AUTH_ERROR",
            "Запрос без авторизации отклонён",
        )

        print("\n8. Отмена бронирований")

        отмена_первого = send_request("cancel_booking", {
            "token": first_token,
            "booking_id": created_booking_id,
        })

        check(
            отмена_первого["success"],
            "Пользователь отменил своё бронирование",
        )

        отмена_второго = send_request("cancel_booking", {
            "token": second_token,
            "booking_id": adjacent_booking_id,
        })

        check(
            отмена_второго["success"],
            "Второе бронирование также успешно отменено",
        )

        повторная_отмена = send_request("cancel_booking", {
            "token": first_token,
            "booking_id": created_booking_id,
        })

        check(
            not повторная_отмена["success"]
            and повторная_отмена["error"]["code"] == "BOOKING_ERROR",
            "Повторная отмена отклонена",
        )

        print("\n9. Проверка отображения отменённых бронирований")

        active_bookings = send_request("my_bookings", {
            "token": first_token,
        })

        check(
            active_bookings["success"]
            and all(
                booking["id"] != created_booking_id
                for booking in active_bookings["data"]["bookings"]
            ),
            "Отменённое бронирование не отображается среди активных",
        )

        all_bookings = send_request("my_bookings", {
            "token": first_token,
            "include_cancelled": True,
        })

        check(
            all_bookings["success"]
            and any(
                booking["id"] == created_booking_id
                and booking["status"] == "cancelled"
                for booking in all_bookings["data"]["bookings"]
            ),
            "Отменённое бронирование доступно в полной истории",
        )

        print("\n10. Проверка журнала аудита")

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT action
                    FROM audit_log
                    WHERE booking_id = %s
                    ORDER BY id;
                    """,
                    (created_booking_id,),
                )
                audit_actions = [
                    row[0] for row in cursor.fetchall()
                ]

        check(
            "booking_created" in audit_actions,
            "Создание бронирования записано в журнал аудита",
        )

        check(
            "booking_cancelled" in audit_actions,
            "Отмена бронирования записана в журнал аудита",
        )

    finally:
        # Если тест завершился ошибкой, стараемся отменить
        # все созданные им активные бронирования.
        for booking_id, token in (
            (created_booking_id, first_token),
            (adjacent_booking_id, second_token),
        ):
            if booking_id is None:
                continue

            try:
                send_request("cancel_booking", {
                    "token": token,
                    "booking_id": booking_id,
                })
            except Exception:
                pass

        # Закрываем локальный пул подключений PostgreSQL.
        close_connection_pool()

    print("\nВсе проверки системы бронирования пройдены!")


if __name__ == "__main__":
    main()