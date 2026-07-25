import logging
from typing import Tuple
from data.database import fetch_query_results, perform_database_operation

logger = logging.getLogger(__name__)

class CategoryRepository:  
    def __init__(self):
        self.columns = ["id", "name", "categoryTypeId", "color", "icon", "threshold"]
        
    def get_all_categories(self):
        """Retrieve all categories with their types."""
        query = """
                SELECT id, name, categoryTypeId, color, icon, threshold
                FROM Category
                ORDER BY name
            """         
        result = fetch_query_results(query)
        if result.empty:
            return {}
        return result.to_dict(orient="records")
        
    def get_category_by_name(self, name: str):
        """Retrieve a category by its name."""
        query = """
                SELECT id, name, categoryTypeId, color, icon, threshold
                FROM Category
                WHERE name = :name
            """
        result = fetch_query_results(query, params={"name": name})
        if result.empty:
            return {}
        return result.to_dict(orient="records")
                   
    def get_category_by_id(self, category_id: int):
        """Retrieve a category by its ID."""
        query = """
                SELECT id, name, categoryTypeId, color, icon, threshold
                FROM Category 
                WHERE id = :id
            """
        result = fetch_query_results(query, params={"id": category_id})
        if result.empty:
            return {}
        return result.to_dict(orient="records")
        
    
    def add_category(self, name: str, categoryTypeId: int, color: str, icon: str, threshold: float) -> Tuple[bool, str]:
        """Add a new Category""" 
        # Check if category already exists
        existing = self.get_category_by_name(name)
        if existing:
            return False, f"Category '{name}' already exists."
            
        query = """
            INSERT INTO Category (name, categoryTypeId, color, icon, threshold)
            VALUES (:name, :categoryTypeId, :color, :icon, :threshold)
        """
        result = perform_database_operation(query, params={
            "name": name,
            "categoryTypeId": categoryTypeId,
            "color": color,
            "icon": icon,
            "threshold": threshold,
        }) 
        return True, f"Category '{name}' added successfully."

    
    def update_category(self, id: int, name: str, categoryTypeId: int, 
                       color: str, icon: str, threshold: float) -> Tuple[bool, str]:
        """Update an existing category."""
        # Check if category exists
        existing = self.get_category_by_id(id)
        if not existing:
            return False, f"Category with ID {id} not found."
        
        # Update category
        query = """
            UPDATE Category 
            SET name = :name,
                categoryTypeId = :categoryTypeId,
                color = :color,
                icon = :icon,
                threshold = :threshold
            WHERE id = :id
        """
        result = perform_database_operation(query, params={
                    "id": id,
                    "name": name,
                    "categoryTypeId": categoryTypeId,
                    "color": color,
                    "icon": icon,
                    "threshold": threshold or 0.0
                })        
        return True, f"Category '{name}' updated successfully."

    def remove_category(self, id: int) -> bool:
        """Remove a category by ID."""  
        # Delete subcategories first (cascade)
        query = 'DELETE FROM SubCategory WHERE categoryId = :id; DELETE FROM Category WHERE id = :id;'
        result = perform_database_operation(query,{"id": id} )
        return True
