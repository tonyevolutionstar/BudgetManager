import logging
from typing import Tuple
import streamlit as st

from data.database import fetch_query_results, perform_database_operation, get_table_columns

logger = logging.getLogger(__name__)

class CategoryRepository:  
    def __init__(self):
        self.columns = get_table_columns("category")  # Cache column names for validation
        
    def get_all_categories(self) -> list[dict]:
        """Retrieve all categories with their types."""
        query = """
                SELECT id, name, categorytypeid, color, icon, threshold
                FROM category
                ORDER BY name
            """         
        result = fetch_query_results(query)
        result["id"] = result["id"].astype(int)
        result["categorytypeid"] = result["categorytypeid"].astype(int)
        
        if result.empty:
            return []
        return result.to_dict(orient="records")
        
    def get_category_by_name(self, name: str) -> list[dict]:
        """Retrieve a category by its name."""
        query = """
                SELECT id, name, categorytypeid, color, icon, threshold
                FROM category
                WHERE name = :name
            """
        result = fetch_query_results(query, params={"name": name})
        if result.empty:
            return []
        return result.to_dict(orient="records")
                   
    def get_category_by_id(self, categoryId: int) -> list[dict]:
        """Retrieve a category by its ID."""
        st.info(f"Fetching category with ID: {categoryId}")
        query = """
                SELECT id, name, categoryTypeId, color, icon, threshold
                FROM Category 
                WHERE id = :id
            """
        result = fetch_query_results(query, params={"id": int(categoryId)})
        if result.empty:
            return []
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
        
        perform_database_operation(query, params={
            "name": name,
            "categoryTypeId": categoryTypeId,
            "color": color,
            "icon": icon,
            "threshold": threshold,
        }) 
        
        logger.info("Category '%s' created.", name)
        return True, f"Category '{name}' added successfully."


    def update_category(self, id: int, name: str, categoryTypeId: int, 
                       color: str, icon: str, threshold: float) -> Tuple[bool, str]:
        """Update an existing category."""
        # Check if category exists
        existing = self.get_category_by_id(id)
        if not existing:
            return False, f"Category {name} not found."
        
        # Update category
        query = """
            UPDATE Category 
            SET name = :name,
                categorytypeid = :categoryTypeId,
                color = :color,
                icon = :icon,
                threshold = :threshold
            WHERE id = :id
        """
        perform_database_operation(query, params={
                    "id": id,
                    "name": name,
                    "categoryTypeId": categoryTypeId,
                    "color": color,
                    "icon": icon,
                    "threshold": threshold or 0.0
        })        
        logger.info("Category '%s' (id=%s) updated.", name, id)
        return True, f"Category '{name}' updated successfully."

    def remove_category(self, id: int) -> Tuple[bool, str]:
        """Remove a category by ID."""  
        # Delete subcategories first (cascade)
        perform_database_operation(
            "DELETE FROM SubCategory WHERE categoryid = :id", {"id": id}
        )
        perform_database_operation(
            "DELETE FROM Category WHERE id = :id", {"id": id}
        )
        logger.info("Category id=%s and its subcategories removed.", id)
        return True, f"Category id={id} and its subcategories removed successfully."
