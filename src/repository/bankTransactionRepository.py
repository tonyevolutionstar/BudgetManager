from datetime import datetime
import logging
from typing import Tuple

from streamlit import empty
from data.database import fetch_query_results, perform_database_operation

logger = logging.getLogger(__name__)

class BankTransactionRepository:
    def get_transactions(self, start_date=None, end_date=None, category_id=None):
        """Retrieve transactions with optional filters."""
        query = """
                SELECT operationDate, description, expense, income, accountingBalance, categoryId, subCategoryId
                FROM BankTransaction
                WHERE 1=1
            """
        params = {}
        
        if start_date:
            query += " AND operationDate >= :start_date"
            params["start_date"] = start_date
        
        if end_date:
            query += " AND operationDate <= :end_date"
            params["end_date"] = end_date
        
        if category_id:
            query += " AND categoryId = :category_id"
            params["category_id"] = category_id
        
        query += " ORDER BY operationDate DESC"
            
        result = fetch_query_results(query, params=params)
        if result.empty:
            return {}
        return result.to_dict(orient="records")  
       
    def get_transaction_by_id(self, id: int):
        """Retrieve a transaction by ID."""
        query = """
                SELECT operationDate, description, expense, income, accountingBalance, categoryId, subCategoryId
                FROM BankTransaction
                WHERE id = :id
        """
        result = fetch_query_results(query, {"id": id})
        if result.empty:
            return {}
        return result.to_dict(orient="records")
    
    def add_transaction(self, operationDate: datetime, description: str, expense: float, income: float, accountingBalance: float, 
                        categoryId: int, subCategoryId: int) -> Tuple[bool, str]:
        """Add a new transaction."""
        query = """
            INSERT INTO BankTransaction(operationDate, description, expense, income, accountingBalance, categoryId, subCategoryId) 
            VALUES (:operationDate, :description, :expense, :income, :accountingBalance, :categoryId, :subCategoryId)
        """
        
        result = perform_database_operation(query, {
            "operationDate": operationDate,
            "description": description,
            "expense": expense,
            "income": income,
            "accountingBalance": accountingBalance,
            "categoryId": categoryId,
            "subCategoryId": subCategoryId
        })
        
        return True, "BankTransaction created."
    
    
    def update_transaction(self, id: int, operationDate: datetime, description: str, expense: float, income: float, accountingBalance: float, 
                        categoryId: int, subCategoryId: int) -> Tuple[bool, str]:
        """Update an existing transaction."""
        
        existing = self.get_transaction_by_id(id)
        if not existing:
            return False, f"Transaction with ID {id} not found"
        
        query = """
            UPDATE BankTransaction 
            SET operationDate = :operationDate, 
                description = :description,
                expense = :expense, 
                income = :income, 
                accountingBalance = :accountingBalance, 
                categoryId = :categoryId, 
                subCategoryId = :subCategoryId
            WHERE id = :id
        """
        
        result = perform_database_operation(query, {
            "operationDate": operationDate,
            "description": description,
            "expense": expense,
            "income": income,
            "accountingBalance": accountingBalance,
            "categoryId": categoryId,
            "subCategoryId": subCategoryId
        })
        
        return True, "BankTransaction created."
        