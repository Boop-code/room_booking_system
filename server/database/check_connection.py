from server.database.connection import (
    get_connection,
    close_connection_pool,
)


def main() -> None:
    """Проверяет подключение к PostgreSQL."""

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        current_database(),
                        current_user,
                        version();
                    """
                )

                database_name, username, version = cursor.fetchone()

                print("Подключение к PostgreSQL успешно!")
                print(f"База данных: {database_name}")
                print(f"Пользователь: {username}")
                print(f"Версия сервера: {version}")

    except Exception as error:
        print("Не удалось подключиться к PostgreSQL.")
        print(f"Ошибка: {error}")

        raise

    finally:
        close_connection_pool()


if __name__ == "__main__":
    main()
