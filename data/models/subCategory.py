from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from data.database import Base

class SubCategory(Base):
    __tablename__ = 'SubCategory'
    
    id = Column("id", Integer, primary_key=True)
    name = Column("name", String, unique=True, nullable=False)
    categoryId = Column("categoryId", Integer, ForeignKey('Category.id'), nullable=False)
    
    # Add relationship back
    category = relationship(
        "Category",
        foreign_keys=[categoryId],
        back_populates="sub_categories",
        lazy="select"
    )
    
    def __repr__(self):
        return f"<SubCategory(id={self.id}, name='{self.name}', categoryId={self.categoryId})>"