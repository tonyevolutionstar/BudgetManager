import logging
from datetime import date, datetime
from typing import Tuple

from data.database import (
    IntegrityViolation,
    fetch_query_results,
    perform_database_operation,
)

logger = logging.getLogger(__name__)

# Aligned with DatabaseSchema.sql: BankTransaction has a SIGNED `amount`
# (negative = expense, positive = income) and a required `accountid`.
_SELECT = """
    SELECT bt.id, bt.accountid, bt.operationdate, bt.valuedate, bt.description,
           bt.amount, bt.accountingbalance,
           bt.categoryid, c.name AS category,
           bt.subcategoryid, sc.name AS subcategory
    FROM BankTransaction bt
    JOIN Category c ON c.id = bt.categoryid
    LEFT JOIN SubCategory sc ON sc.id = bt.subcategoryid
"""


def _validate(description: str, amount: float) -> str | None:
    if not description or not description.strip():
        return "Description is required."
    if amount is None:
        return "Amount is required."
    return None


class BankTransactionRepository:

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_transactions(
        self,
        account_id: int | None = None,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        category_id: int | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Retrieve transactions with optional filters, newest first."""
        clauses: list[str] = []
        params: dict = {}

        if account_id is not None:
            clauses.append("bt.accountid = :account_id")
            params["account_id"] = int(account_id)
        if start_date is not None:
            clauses.append("bt.operationdate >= :start_date")
            params["start_date"] = start_date
        if end_date is not None:
            clauses.append("bt.operationdate <= :end_date")
            params["end_date"] = end_date
        if category_id is not None:
            clauses.append("bt.categoryid = :category_id")
            params["category_id"] = int(category_id)

        query = _SELECT
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY bt.operationdate DESC, bt.id DESC"
        if limit is not None:
            query += " LIMIT :limit"
            params["limit"] = int(limit)

        result = fetch_query_results(query, params=params)
        if result.empty:
            return []
        result["amount"] = result["amount"].astype(float)
        result["accountingbalance"] = result["accountingbalance"].astype(float)
        return result.to_dict(orient="records")

    def get_transaction_by_id(self, id: int) -> list[dict]:
        result = fetch_query_results(_SELECT + " WHERE bt.id = :id", params={"id": int(id)})
        if result.empty:
            return []
        result["amount"] = result["amount"].astype(float)
        result["accountingbalance"] = result["accountingbalance"].astype(float)
        return result.to_dict(orient="records")

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def add_transaction(
        self,
        accountId: int,
        operationDate: date | datetime,
        description: str,
        amount: float,
        accountingBalance: float,
        categoryId: int,
        subCategoryId: int | None = None,
        valueDate: date | datetime | None = None,
    ) -> Tuple[bool, str]:
        """Insert a transaction. `amount` is signed (negative = expense).

        Re-importing the same statement is a no-op when the unique index from
        data/migrations/001_transaction_dedupe_index.sql exists.
        """
        error = _validate(description, amount)
        if error:
            return False, error

        try:
            inserted = perform_database_operation(
                """
                INSERT INTO BankTransaction
                    (accountid, operationdate, valuedate, description, amount,
                     accountingbalance, categoryid, subcategoryid)
                VALUES
                    (:accountId, :operationDate, :valueDate, :description, :amount,
                     :accountingBalance, :categoryId, :subCategoryId)
                ON CONFLICT DO NOTHING
                """,
                {
                    "accountId": int(accountId),
                    "operationDate": operationDate,
                    "valueDate": valueDate,
                    "description": description.strip(),
                    "amount": round(float(amount), 2),
                    "accountingBalance": round(float(accountingBalance), 2),
                    "categoryId": int(categoryId),
                    "subCategoryId": int(subCategoryId) if subCategoryId is not None else None,
                },
            )
        except IntegrityViolation:
            return False, "Invalid account, category or subcategory."

        if inserted == 0:
            return False, "Duplicate transaction, skipped."
        logger.info("BankTransaction created.")
        return True, "BankTransaction created."

    def update_transaction(
        self,
        id: int,
        operationDate: date | datetime,
        description: str,
        amount: float,
        accountingBalance: float,
        categoryId: int,
        subCategoryId: int | None = None,
        valueDate: date | datetime | None = None,
    ) -> Tuple[bool, str]:
        error = _validate(description, amount)
        if error:
            return False, error

        try:
            updated = perform_database_operation(
                """
                UPDATE BankTransaction
                SET operationdate     = :operationDate,
                    valuedate         = :valueDate,
                    description       = :description,
                    amount            = :amount,
                    accountingbalance = :accountingBalance,
                    categoryid        = :categoryId,
                    subcategoryid     = :subCategoryId
                WHERE id = :id
                """,
                {
                    "id": int(id),
                    "operationDate": operationDate,
                    "valueDate": valueDate,
                    "description": description.strip(),
                    "amount": round(float(amount), 2),
                    "accountingBalance": round(float(accountingBalance), 2),
                    "categoryId": int(categoryId),
                    "subCategoryId": int(subCategoryId) if subCategoryId is not None else None,
                },
            )
        except IntegrityViolation:
            return False, "Invalid category or subcategory."

        if updated == 0:
            return False, f"Transaction with ID {id} not found."
        logger.info("BankTransaction id=%s updated.", id)
        return True, "BankTransaction updated."