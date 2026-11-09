import os
from pathlib import Path
from threading import Lock
from contextlib import contextmanager
from typing import Iterator

from dotenv import load_dotenv
from psycopg import Connection
from psycopg.conninfo import make_conninfo
from psycopg_pool import ConnectionPool


# Корневая папка проекта
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Загружаем настройки из .env
load_dotenv(PROJECT_ROOT / ".env")


_pool: ConnectionPool | None = None
_pool_lock = Lock()


def _get_database_settings() -> dict:
    """Получает настройки подключения к PostgreSQL."""

    required_variables = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    ]

    missing_variables = [
        variable
        for variable in required_variables
        if not os.getenv(variable)
    ]

    if missing_variables:
        raise RuntimeError(
            "Не заданы переменные окружения: "
            + ", ".join(missing_variables)
        )

    return {
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
    }


def get_connection_pool() -> ConnectionPool:
    """Создаёт пул подключений или возвращает существующий."""

    global _pool

    with _pool_lock:
        if _pool is None:
            settings = _get_database_settings()

            conninfo = make_conninfo(**settings)

            min_size = int(os.getenv("DB_POOL_MIN_SIZE", "1"))
            max_size = int(os.getenv("DB_POOL_MAX_SIZE", "10"))

            if min_size < 1 or max_size < min_size:
                raise ValueError(
                    "Некорректные настройки пула подключений."
                )

            _pool = ConnectionPool(
                conninfo=conninfo,
                min_size=min_size,
                max_size=max_size,
                open=False,
            )

            _pool.open(wait=True)

        return _pool


@contextmanager
def get_connection() -> Iterator[Connection]:
    """Предоставляет соединение из пула."""

    pool = get_connection_pool()

    with pool.connection() as connection:
        yield connection


def close_connection_pool() -> None:
    """Закрывает пул подключений."""

    global _pool

    with _pool_lock:
        if _pool is not None:
            _pool.close()
            _pool = None
