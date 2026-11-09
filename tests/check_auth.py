import json
import secrets
import socket


HOST = "127.0.0.1"
PORT = 5050


def send_request(action: str, data: dict) -> dict:
    request = {
        "request_id": secrets.token_hex(8),
        "action": action,
        "data": data,
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
    username = "test_" + secrets.token_hex(4)
    password = "TestPassword123"
    full_name = "Тестовый Пользователь"

    print("Проверка регистрации и авторизации\n")

    # 1. Регистрация
    registration = send_request("register", {
        "username": username,
        "password": password,
        "full_name": full_name,
    })

    check(
        registration.get("success") is True,
        "Новый пользователь успешно зарегистрирован",
    )

    user = registration["data"]["user"]

    check(user["username"] == username, "Логин сохранён правильно")
    check(user["role"] == "user", "Пользователю назначена роль user")
    check("password_hash" not in user, "Хеш пароля не возвращается клиенту")

    # 2. Повторная регистрация с тем же логином
    duplicate = send_request("register", {
        "username": username,
        "password": password,
        "full_name": full_name,
    })

    check(
        duplicate.get("success") is False,
        "Повторная регистрация с тем же логином отклонена",
    )

    # 3. Регистрация с коротким паролем
    invalid_registration = send_request("register", {
        "username": "invalid_user",
        "password": "123",
        "full_name": "Тестовый Пользователь",
    })

    check(
        invalid_registration.get("success") is False,
        "Короткий пароль отклонён",
    )

    # 4. Вход с неправильным паролем
    wrong_login = send_request("login", {
        "username": username,
        "password": "WrongPassword123",
    })

    check(
        wrong_login.get("success") is False,
        "Вход с неправильным паролем отклонён",
    )

    # 5. Успешный вход
    login = send_request("login", {
        "username": username,
        "password": password,
    })

    check(login.get("success") is True, "Вход выполнен успешно")

    login_data = login["data"]
    token = login_data["token"]

    check(bool(token), "Сервер выдал токен сессии")
    check(
        login_data["user"]["username"] == username,
        "Данные вошедшего пользователя корректны",
    )

    # 6. Выход
    logout = send_request("logout", {"token": token})

    check(logout.get("success") is True, "Выход выполнен успешно")

    # 7. Повторный выход с тем же токеном
    repeated_logout = send_request("logout", {"token": token})

    check(
        repeated_logout.get("success") is False,
        "Повторное завершение сессии отклонено",
    )

    print("\nВсе проверки авторизации пройдены!")


if __name__ == "__main__":
    main()