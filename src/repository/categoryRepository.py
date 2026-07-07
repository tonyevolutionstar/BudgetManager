import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from data.database import get_db_connection
from data.models.category import Category
from data.models.categoryType import CategoryType
from data.models.subCategory import SubCategory
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import joinedload   
from typing import Optional, List, Dict, Tuple
import logging
import pandas as pd

logger = logging.getLogger(__name__)

class CategoryRepository:
    def __init__(self):
        self.session = get_db_connection().session
    
    def get_category_by_name(self, name: str) -> Optional[Category]:
        """Retrieve a category by its name."""
        try:
            return self.session.query(Category).filter_by(name=name).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving category by name '{name}': {str(e)}")
            return None
        finally:
            self.session.close()
    
    def get_category_by_id(self, category_id: int) -> Optional[Category]:
        """Retrieve a category by its ID."""
        try:
            return self.session.query(Category).filter(Category.id == category_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving category by ID '{category_id}': {str(e)}")
            return None
        finally:
            self.session.close()
    
    def get_all_categories(self) -> List[Dict]:
        """Retrieve all categories with their relationships as dictionaries."""
        try:
            # Use joinedload to eager load relationships
            categories = (self.session.query(Category)
                        .options(joinedload(Category.category_type))
                        .options(joinedload(Category.sub_categories))
                        .order_by(Category.name)
                        .all())
        
            result = []
            for cat in categories:
                result.append({
                    'id': cat.id,
                    'name': cat.name,
                    'categoryTypeId': cat.categoryTypeId,
                    'type_name': cat.category_type.name if cat.category_type else None,
                    'color': cat.color,
                    'icon': cat.icon,
                    'threshold': cat.threshold,
                    'subcategories': [{'id': s.id, 'name': s.name} for s in cat.sub_categories]
                })
            return result
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving categories: {str(e)}")
            return []
        finally:
            self.session.close()
    
    def get_categories_with_details(self) -> List[Dict]:
        """Retrieve all categories with their type and subcategory details as dictionaries."""
        try:
            results = (self.session.query(
                    Category.id,
                    Category.name,
                    Category.categoryTypeId,
                    Category.color,
                    Category.icon,
                    Category.threshold,
                    CategoryType.name.label('type_name')
                )
                .join(CategoryType, Category.categoryTypeId == CategoryType.id)
                .order_by(Category.name)
                .all())
            
            # Convert to list of dicts
            categories = []
            for row in results:
                # Get subcategories for this category
                subcategories = (self.session.query(SubCategory)
                               .filter(SubCategory.categoryId == row.id)
                               .all())
                
                categories.append({
                    'id': row.id,
                    'name': row.name,
                    'categoryTypeId': row.categoryTypeId,
                    'type_name': row.type_name,
                    'color': row.color,
                    'icon': row.icon,
                    'threshold': row.threshold,
                    'subcategories': [{'id': s.id, 'name': s.name} for s in subcategories]
                })
            
            return categories
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving categories with details: {str(e)}")
            return []
        finally:
            self.session.close()
    
    def get_categories_dataframe(self) -> pd.DataFrame:
        """Return categories as a pandas DataFrame."""
        try:
            categories = self.get_categories_with_details()
            if categories:
                return pd.DataFrame(categories)
            return pd.DataFrame(columns=['id', 'name', 'categoryTypeId', 'type_name', 'color', 'icon', 'threshold', 'subcategories'])
        except Exception as e:
            logger.error(f"Error creating DataFrame: {str(e)}")
        return pd.DataFrame()
    
    def insert_category(self, name: str, categoryTypeId: int, color: str = "", 
                       icon: str = "", threshold: float = 0.0) -> Tuple[Optional[Category], str]:
        """Insert a new category into the database."""
        try:
            # Check if category already exists
            existing_category = self.session.query(Category).filter_by(name=name).first()
            if existing_category:
                return None, f"Category '{name}' already exists."
            
            # Create new category
            new_category = Category(
                name=name,
                categoryTypeId=categoryTypeId,
                color=color or "#808080",
                icon=icon or "📂",
                threshold=threshold or 0.0
            )
            
            self.session.add(new_category)
            self.session.commit()
            self.session.refresh(new_category)
            
            logger.info(f"Category '{name}' added successfully with ID: {new_category.id}")
            return new_category, f"Category '{name}' added successfully."
            
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Integrity error inserting category '{name}': {str(e)}")
            return None, f"Category '{name}' already exists or violates constraints."
        
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error inserting category '{name}': {str(e)}")
            return None, f"Database error: {str(e)}"
        
        except Exception as e:
            self.session.rollback()
            logger.error(f"Unexpected error inserting category '{name}': {str(e)}")
            return None, f"Unexpected error: {str(e)}"
        
        finally:
            self.session.close()
    
    def update_category(self, category_id: int, **kwargs) -> Tuple[bool, str]:
        """Update a category by ID with validation."""
        try:
            category = self.session.query(Category).filter(Category.id == category_id).first()
            if not category:
                return False, f"Category with ID {category_id} not found."
            
            # Validate and update fields
            allowed_fields = ['name', 'categoryTypeId', 'color', 'icon', 'threshold']
            updated_fields = []
            
            for key, value in kwargs.items():
                if key in allowed_fields and hasattr(category, key):
                    # Check if name is being changed and if new name already exists
                    if key == 'name' and value != category.name:
                        existing = self.session.query(Category).filter_by(name=value).first()
                        if existing:
                            return False, f"Category name '{value}' already exists."
                    
                    setattr(category, key, value)
                    updated_fields.append(key)
            
            if not updated_fields:
                return False, "No valid fields to update."
            
            # Commit changes
            self.session.commit()
            self.session.refresh(category)
            
            logger.info(f"Category '{category.name}' updated successfully. Fields: {updated_fields}")
            return True, f"Category updated successfully."
            
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Integrity error updating category {category_id}: {str(e)}")
            return False, f"Category name already exists or violates constraints."
        
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error updating category {category_id}: {str(e)}")
            return False, f"Database error: {str(e)}"
        
        except Exception as e:
            self.session.rollback()
            logger.error(f"Unexpected error updating category {category_id}: {str(e)}")
            return False, f"Unexpected error: {str(e)}"
        
        finally:
            self.session.close()
    
    def delete_category(self, category_id: int) -> Tuple[bool, str]:
        """Delete a category by ID."""
        try:
            category = self.session.query(Category).filter(Category.id == category_id).first()
            if not category:
                return False, f"Category with ID {category_id} not found."
            
            # Check if category has subcategories
            subcategories = self.session.query(SubCategory).filter(SubCategory.categoryId == category_id).all()
            if subcategories:
                # Option 1: Delete subcategories first
                for sub in subcategories:
                    self.session.delete(sub)
                logger.info(f"Deleted {len(subcategories)} subcategories for category {category_id}")
                
                # Option 2: Or return error
                # return False, f"Category has {len(subcategories)} subcategories. Remove them first."
            
            # Delete the category
            self.session.delete(category)
            self.session.commit()
            
            logger.info(f"Category '{category.name}' deleted successfully")
            return True, f"Category '{category.name}' deleted successfully."
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error deleting category {category_id}: {str(e)}")
            return False, f"Database error: {str(e)}"
        
        except Exception as e:
            self.session.rollback()
            logger.error(f"Unexpected error deleting category {category_id}: {str(e)}")
            return False, f"Unexpected error: {str(e)}"
        
        finally:
            self.session.close()
    
    
    def get_categories_by_type(self, type_id: int) -> List[Category]:
        """Get all categories of a specific type."""
        try:
            return (self.session.query(Category)
                    .filter(Category.categoryTypeId == type_id)
                    .order_by(Category.name)
                    .all())
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving categories by type {type_id}: {str(e)}")
            return []
        finally:
            self.session.close()
    
    def get_category_stats(self) -> Dict:
        """Get statistics about categories."""
        try:
            total = self.session.query(Category).count()
            
            # Count by type
            type_counts = {}
            types = self.session.query(CategoryType).all()
            for type_obj in types:
                count = self.session.query(Category).filter(Category.categoryTypeId == type_obj.id).count()
                type_counts[type_obj.name] = count
            
            return {
                'total_categories': total,
                'by_type': type_counts
            }
        except SQLAlchemyError as e:
            logger.error(f"Error getting category stats: {str(e)}")
            return {'total_categories': 0, 'by_type': {}}
        finally:
            self.session.close()
    