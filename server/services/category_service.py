from typing import Any

from server.repositories.category_repository import CategoryRepository


class CategoryService:
    """Сервис получения категорий помещений."""

    def __init__(
        self,
        repository: CategoryRepository | None = None,
    ) -> None:
        self.repository = repository or CategoryRepository()

    def get_categories(self) -> list[dict[str, Any]]:
        """Возвращает список категорий."""

        return self.repository.get_all()
