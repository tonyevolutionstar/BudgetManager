from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from data.database import Base

class Category(Base):
    __tablename__ = 'Category'
    
    id = Column("id", Integer, primary_key=True)
    name = Column("name", String, unique=True, nullable=False)
    categoryTypeId = Column("categoryTypeId", Integer, ForeignKey('CategoryType.id'), nullable=False)
    color = Column("color", String, default="#808080")
    icon = Column("icon", String, default="📂")
    threshold = Column("threshold", Float, default=0.0)
    
    # Add relationships back
    category_type = relationship(
        "CategoryType",
        foreign_keys=[categoryTypeId],
        back_populates="categories",
        lazy="select"
    )
    
    sub_categories = relationship(
        "SubCategory",
        foreign_keys="SubCategory.categoryId",
        back_populates="category",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    bank_transactions = relationship(
        "BankTransaction",
        foreign_keys="BankTransaction.categoryId",
        back_populates="category",
        lazy="select"
    )
    
    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"