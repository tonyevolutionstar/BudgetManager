from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from data.database import Base
from datetime import datetime

# Define BankTransaction model
class BankTransaction(Base):
    __tablename__ = 'BankTransaction'

    id = Column("id", Integer, primary_key=True)
    operationDate = Column("operationDate", DateTime, nullable=False, default=datetime.utcnow)
    description = Column("description", String, nullable=False)
    expense = Column("expense", Float, nullable=False, default=0.0)
    income = Column("income", Float, nullable=False, default=0.0)
    accountingBalance = Column("accountingBalance", Float, nullable=False, default=0.0)
    categoryId = Column("categoryId", Integer, ForeignKey('Category.id'), nullable=False)  
    subCategoryId = Column("subCategoryId", Integer, ForeignKey('SubCategory.id'), nullable=True)
    
    # Add relationships back
    category = relationship(
        "Category",
        foreign_keys=[categoryId],
        back_populates="bank_transactions",
        lazy="select"
    )
    
    sub_category = relationship(
        "SubCategory",
        foreign_keys=[subCategoryId],
        lazy="select"
    )
         
    def __repr__(self):
        return f"<BankTransaction(id={self.id}, description='{self.description}')>"