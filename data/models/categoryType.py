from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from data.database import Base

class CategoryType(Base):
    __tablename__ = 'CategoryType'
    
    id = Column("id", Integer, primary_key=True)
    name = Column("name", String, unique=True, nullable=False)
    
    # Add relationship back
    categories = relationship(
        "Category",
        foreign_keys="Category.categoryTypeId",
        back_populates="category_type",
        lazy="select"
    )
    
    def __repr__(self):
        return f"<CategoryType(id={self.id}, name='{self.name}')>"