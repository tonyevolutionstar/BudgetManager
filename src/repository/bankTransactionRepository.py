import logging
from datetime import datetime
from typing import Tuple

from data.database import fetch_query_results, perform_database_operation

logger = logging.getLogger(__name__)

class BankTransactionRepository:

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_transactions(
        self,
        start_date=None,
        end_date=None,
        category_id=None,
    ) -> list[dict]:
        """Retrieve transactions with optional date / category filters."""
        query = """
            SELECT operationDate, description, expense, income,
                   accountingBalance, categoryId, subCategoryId
            FROM BankTransaction
        """
        params: dict = {}

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
            return []
        return result.to_dict(orient="records")

    def get_transaction_by_id(self, id: int) -> list[dict]:
        query = """
            SELECT operationDate, description, expense, income,
                   accountingBalance, categoryid, subcategoryid
            FROM BankTransaction
            WHERE id = :id
        """
        result = fetch_query_results(query, {"id": id})
        if result.empty:
            return []
        return result.to_dict(orient="records")

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def add_transaction(
        self,
        operationDate: datetime,
        description: str,
        expense: float,
        income: float,
        accountingBalance: float,
        categoryId: int,
        subCategoryId: int,
    ) -> Tuple[bool, str]:
        query = """
            INSERT INTO BankTransaction
                (operationDate, description, expense, income,
                 accountingBalance, categoryid, subcategoryid)
            VALUES
                (:operationDate, :description, :expense, :income,
                 :accountingBalance, :categoryId, :subCategoryId)
        """
        perform_database_operation(query, {
            "operationDate":     operationDate,
            "description":       description,
            "expense":           expense,
            "income":            income,
            "accountingBalance": accountingBalance,
            "categoryid":        categoryId,
            "subcategoryid":     subCategoryId,
        })
        logger.info("BankTransaction created for '%s'.", description)
        return True, "BankTransaction created."

    def update_transaction(self, id: int, operationDate: datetime, description: str, expense: float, 
                           income: float, accountingBalance: float, categoryId: int, subCategoryId: int
    ) -> Tuple[bool, str]:
        existing = self.get_transaction_by_id(id)
        if not existing:
            return False, f"Transaction with ID {id} not found."

        query = """
            UPDATE BankTransaction
            SET operationDate     = :operationDate,
                description       = :description,
                expense           = :expense,
                income            = :income,
                accountingBalance = :accountingBalance,
                categoryid        = :categoryId,
                subcategoryid     = :subCategoryId
            WHERE id = :id
        """
        perform_database_operation(query, {
            "id":                id,
            "operationDate":     operationDate,
            "description":       description,
            "expense":           expense,
            "income":            income,
            "accountingBalance": accountingBalance,
            "categoryid":        categoryId,
            "subcategoryid":     subCategoryId,
        })
        logger.info("BankTransaction id=%s updated.", id)
        return True, "BankTransaction updated."
