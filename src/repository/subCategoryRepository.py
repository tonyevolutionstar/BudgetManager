from data.database import get_db_connection
from data.models.subCategory import SubCategory
from data.models.category import Category
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class SubCategoryRepository:
    def __init__(self):
        self.session = get_db_connection().session
    
    def get_sub_categories(self) -> List[Dict]:
        """Retrieve all subcategories."""
        try:
            subs = self.session.query(SubCategory).order_by(SubCategory.name).all()
            return [{'id': s.id, 'name': s.name, 'categoryId': s.categoryId} for s in subs]
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving subcategories: {str(e)}")
            return []
        finally:
            self.session.close()
    
    def add_sub_category(self, categoryId: int, name: str) -> bool:
        """Add a new subcategory."""
        try:
            # Check if category exists
            category = self.session.query(Category).filter(Category.id == categoryId).first()
            if not category:
                return False
            
            # Check if subcategory already exists for this category
            existing = self.session.query(SubCategory).filter(
                SubCategory.categoryId == categoryId,
                SubCategory.name == name
            ).first()
            if existing:
                return False
            
            new_sub = SubCategory(
                categoryId=categoryId,
                name=name
            )
            
            self.session.add(new_sub)
            self.session.commit()
            
            logger.info(f"Subcategory '{name}' added to category {categoryId}")
            return True
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error adding subcategory: {str(e)}")
            return False
        finally:
            self.session.close()
    
    def remove_sub_category(self, id: int) -> bool:
        """Remove a subcategory by ID."""
        try:
            sub = self.session.query(SubCategory).filter(SubCategory.id == id).first()
            if not sub:
                return False
            
            self.session.delete(sub)
            self.session.commit()
            
            logger.info(f"Subcategory '{sub.name}' removed successfully")
            return True
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error removing subcategory: {str(e)}")
            return False
        finally:
            self.session.close()