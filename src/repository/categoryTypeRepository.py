import logging
from functools import cached_property

from data.database import fetch_query_results, get_table_columns

logger = logging.getLogger(__name__)


class CategoryTypeRepository:
    @cached_property
    def columns(self) -> list[str]:
        """Column names (loaded lazily, so constructing the repository doesn't hit the DB)."""
        return get_table_columns("categorytype")

    def get_category_types(self) -> list[dict]:
        """Retrieve all category types."""
        result = fetch_query_results("SELECT id, name FROM CategoryType ORDER BY name")
        if result.empty:
            return []
        result["id"] = result["id"].astype(int)
        return result.to_dict(orient="records")

    def get_category_type_name_by_id(self, type_id: int) -> list[dict]:
        """Retrieve a category type name by its ID."""
        result = fetch_query_results(
            "SELECT name FROM CategoryType WHERE id = :id", params={"id": int(type_id)}
        )
        return [] if result.empty else result.to_dict(orient="records")

    def get_category_type_id_by_name(self, name: str) -> list[dict]:
        """Retrieve a category type id by its name."""
        result = fetch_query_results(
            "SELECT id FROM CategoryType WHERE name = :name", params={"name": name}
        )
        return [] if result.empty else result.to_dict(orient="records")