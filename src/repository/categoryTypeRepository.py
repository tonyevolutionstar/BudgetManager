import logging
from data.database import fetch_query_results, perform_database_operation, get_table_columns

logger = logging.getLogger(__name__)

class CategoryTypeRepository:
    def __init__(self):
        self.columns = get_table_columns("categorytype")  # Cache column names for validation
        
    def get_category_types(self) -> list[dict]:
        """Retrieve all category types."""
        query = "SELECT id, name FROM CategoryType ORDER BY name"
        result = fetch_query_results(query)
        result["id"] = result["id"].astype(int)
        if result.empty:
            return []
        return result.to_dict(orient="records")
    
    def get_category_type_name_by_id(self, type_id: int) -> list[dict]:
        """Retrieve a category type by its ID."""
        query = "SELECT name FROM CategoryType WHERE id = :id"
        result = fetch_query_results(query, params={"id": type_id})
        if result.empty:
            return {}
        return result.to_dict(orient="records")
        
    def get_category_type_id_by_name(self, name: str):
        """Retrieve a category type by its name."""
        query = "SELECT id FROM CategoryType WHERE name = :name"
        result = fetch_query_results(query, params={"name": name})
        if result.empty:
            return {}
        return result.to_dict(orient="records")
        