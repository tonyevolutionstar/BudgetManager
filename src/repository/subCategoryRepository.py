import logging
from data.database import fetch_query_results, perform_database_operation

logger = logging.getLogger(__name__)

class SubCategoryRepository:
    def __init__(self):
        self.columns = ["id", "name", "categoryId"]
        
    def get_sub_categories(self):
        """Retrieve all subcategories."""
        query = """
            SELECT id, name, categoryId
            FROM SubCategory 
        """
        result = fetch_query_results(query)
        if result.empty:
            return {}
        return result.to_dict(orient="records")
    
    def get_sub_categories_by_category(self, category_id: int):
        """Retrieve subcategories for a specific category."""
        query = """
                SELECT sc.id, sc.name as subCategory, c.Name as category 
                FROM SubCategory sc 
                JOIN Category c on sc.categoryId = c.id
                WHERE categoryId = :category_id
                ORDER BY c.name, sc.name
            """
        result = fetch_query_results(query, params={"category_id": category_id})
        if result.empty:
            return {}
        return result.to_dict(orient="records")
    
    def add_sub_category(self, categoryId: int, name: str) -> tuple[bool, str]:
        """Add a new subcategory."""
        existing_query = """
            SELECT id
            FROM SubCategory
            WHERE categoryId = :categoryId
              AND LOWER(name) = LOWER(:name)
        """
        existing = fetch_query_results(existing_query, params={"categoryId": categoryId, "name": name})
        if not existing.empty:
            return False, f"Subcategory '{name}' already exists."

        insert_query = """
            INSERT INTO SubCategory (name, categoryId)
            VALUES (:name, :categoryId)
        """
        perform_database_operation(insert_query, params={"name": name, "categoryId": categoryId})

        return True, f"Subcategory '{name}' added successfully."
       
    def remove_sub_category(self, id: int) -> bool:
        """Remove a subcategory by ID."""
        query = 'DELETE FROM SubCategory WHERE id = :id'
        result = perform_database_operation(query=query, params={"id": id})
        return True