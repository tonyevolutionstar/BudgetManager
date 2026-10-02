import logging
from typing import Tuple

from data.database import (
    IntegrityViolation,
    fetch_query_results,
    perform_database_operation,
)

logger = logging.getLogger(__name__)

MAX_NAME = 200  # SubCategory.name varchar(200)


class SubCategoryRepository:
    def __init__(self):
        self.columns = ["id", "name", "categoryId"]

    def get_sub_categories(self) -> list[dict]:
        """Retrieve all subcategories (keys: id, name, categoryid)."""
        result = fetch_query_results("SELECT id, name, categoryId FROM SubCategory")
        return [] if result.empty else result.to_dict(orient="records")

    def get_sub_categories_by_category(self, category_id: int) -> list[dict]:
        """Retrieve subcategories for a specific category."""
        result = fetch_query_results(
            """
            SELECT sc.id, sc.name AS subCategory, c.name AS category
            FROM SubCategory sc
            JOIN Category c ON sc.categoryId = c.id
            WHERE sc.categoryId = :category_id
            ORDER BY c.name, sc.name
            """,
            params={"category_id": int(category_id)},
        )
        return [] if result.empty else result.to_dict(orient="records")

    def add_sub_category(self, categoryId: int, name: str) -> Tuple[bool, str]:
        """Add a new subcategory. Returns (success, message)."""
        name = (name or "").strip()
        if not name:
            return False, "Subcategory name is required."
        if len(name) > MAX_NAME:
            return False, f"Subcategory name must be at most {MAX_NAME} characters."

        existing = fetch_query_results(
            """
            SELECT id FROM SubCategory
            WHERE categoryId = :categoryId AND LOWER(name) = LOWER(:name)
            """,
            params={"categoryId": int(categoryId), "name": name},
        )
        if not existing.empty:
            return False, f"Subcategory '{name}' already exists."

        try:
            perform_database_operation(
                "INSERT INTO SubCategory (name, categoryId) VALUES (:name, :categoryId)",
                params={"name": name, "categoryId": int(categoryId)},
            )
        except IntegrityViolation:
            # UNIQUE (name, categoryId) race, or the category no longer exists.
            return False, f"Could not add '{name}': duplicate name or unknown category."

        return True, f"Subcategory '{name}' added successfully."

    def remove_sub_category(self, id: int) -> Tuple[bool, str]:
        """Remove a subcategory unless something still references it."""
        usage = fetch_query_results(
            """
            SELECT
              (SELECT COUNT(*) FROM BankTransaction    WHERE subcategoryid   = :id) AS transactions,
              (SELECT COUNT(*) FROM ClassificationRule WHERE subcategoryid   = :id) AS rules,
              (SELECT COUNT(*) FROM MLTrainingSample   WHERE sub_category_id = :id) AS samples
            """,
            params={"id": int(id)},
        ).iloc[0]
        blockers = [f"{int(usage[k])} {label}" for k, label in (
            ("transactions", "transaction(s)"),
            ("rules", "classification rule(s)"),
            ("samples", "training sample(s)"),
        ) if int(usage[k])]
        if blockers:
            return False, "Cannot remove this subcategory, it is still used by " + ", ".join(blockers) + "."

        removed = perform_database_operation(
            "DELETE FROM SubCategory WHERE id = :id", params={"id": int(id)}
        )
        if removed == 0:
            return False, f"Subcategory with ID {id} not found."
        return True, "Subcategory removed successfully."