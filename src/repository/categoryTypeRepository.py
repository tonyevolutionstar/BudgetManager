from data.database import get_db_connection
from data.models.categoryType import CategoryType
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class CategoryTypeRepository:
    def __init__(self):
        self.session = get_db_connection().session
    
    def get_category_types(self) -> List[Dict]:
        """Retrieve all category types."""
        try:
            types = self.session.query(CategoryType).order_by(CategoryType.name).all()
            return [{'id': t.id, 'name': t.name} for t in types]
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving category types: {str(e)}")
            return []
        finally:
            self.session.close()
    
    def get_category_type_by_id(self, type_id: int):
        """Retrieve a category type by its ID."""
        try:
            return self.session.query(CategoryType).filter(CategoryType.id == type_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving category type by ID {type_id}: {str(e)}")
            return None
        finally:
            self.session.close()