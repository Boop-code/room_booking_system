from typing import Any

from psycopg.rows import dict_row

from server.database.connection import get_connection


class CategoryRepository:
    """Репозиторий для работы с категориями помещений."""

    def get_all(self) -> list[dict[str, Any]]:
        """Возвращает все категории помещений."""

        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        name,
                        description
                    FROM categories
                    ORDER BY name;
                    """
                )

                return [dict(row) for row in cursor.fetchall()]
