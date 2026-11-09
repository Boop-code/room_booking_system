import logging
import os

from dotenv import load_dotenv

from server.database.connection import (
    get_connection,
    close_connection_pool,
)
from server.network.tcp_server import TCPServer


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def check_database_connection() -> None:
    """Проверяет доступность базы данных."""

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()

    logging.info("Подключение к PostgreSQL успешно.")


def main() -> None:
    """Запускает сервер приложения."""

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s [%(levelname)s] "
            "%(threadName)s: %(message)s"
        ),
    )

    host = os.getenv("TCP_HOST", "127.0.0.1")
    port = int(os.getenv("TCP_PORT", "5050"))
    max_workers = int(os.getenv("SERVER_MAX_WORKERS", "10"))

    server = TCPServer(
        host=host,
        port=port,
        max_workers=max_workers,
    )

    try:
        check_database_connection()
        server.serve_forever()

    except KeyboardInterrupt:
        logging.info("Получена команда остановки.")

    except Exception:
        logging.exception("Ошибка запуска сервера.")
        raise

    finally:
        server.stop()
        close_connection_pool()
        logging.info("Сервер остановлен.")


if __name__ == "__main__":
    main()
