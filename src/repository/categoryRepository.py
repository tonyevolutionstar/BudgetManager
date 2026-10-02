import logging
import re
from functools import cached_property
from typing import Tuple

from data.database import (
    IntegrityViolation,
    execute_statements,
    fetch_query_results,
    get_table_columns,
    perform_database_operation,
)

logger = logging.getLogger(__name__)

_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
MAX_NAME = 100            # Category.NAME varchar(100)
MAX_ICON = 10             # Category.icon varchar(10)
MAX_BUDGET = 99_999_999.99  # Category.MonthlyBudget NUMERIC(10, 2)


def _validate(name: str, color: str | None, icon: str | None, monthly_budget: float | None) -> str | None:
    """Return an error message, or None when the input is valid."""
    if not name or not name.strip():
        return "Category name is required."
    if len(name.strip()) > MAX_NAME:
        return f"Category name must be at most {MAX_NAME} characters."
    if color and not _COLOR_RE.match(color):
        return "Color must look like #RRGGBB."
    if icon and len(icon) > MAX_ICON:
        return f"Icon must be at most {MAX_ICON} characters."
    if monthly_budget is not None and not (0 <= float(monthly_budget) <= MAX_BUDGET):
        return "Monthly budget must be between 0 and 99,999,999.99."
    return None


class CategoryRepository:
    @cached_property
    def columns(self) -> list[str]:
        """Column names (loaded lazily, so constructing the repository doesn't hit the DB)."""
        return get_table_columns("category")

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_all_categories(self) -> list[dict]:
        """Retrieve all categories.

        Keys are lowercase (as returned by PostgreSQL): id, name, categorytypeid,
        color, icon, monthlybudget. monthlybudget is a float (not Decimal) so it
        can be divided by float spend values in the dashboard.
        """
        result = fetch_query_results(
            """
            SELECT id, name, categorytypeid, color, icon, monthlybudget
            FROM Category
            ORDER BY name
            """
        )
        if result.empty:
            return []
        result["id"] = result["id"].astype(int)
        result["categorytypeid"] = result["categorytypeid"].astype(int)
        result["monthlybudget"] = result["monthlybudget"].astype(float)
        return result.to_dict(orient="records")

    def get_category_by_name(self, name: str) -> list[dict]:
        """Retrieve a category by name (case-insensitive)."""
        result = fetch_query_results(
            "SELECT * FROM Category WHERE LOWER(name) = LOWER(:name)",
            params={"name": name.strip()},
        )
        return [] if result.empty else result.to_dict(orient="records")

    def get_category_by_id(self, categoryId: int) -> list[dict]:
        """Retrieve a category by its ID."""
        result = fetch_query_results(
            "SELECT * FROM Category WHERE id = :id",
            params={"id": int(categoryId)},
        )
        return [] if result.empty else result.to_dict(orient="records")

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def add_category(self, name: str, categoryTypeId: int, color: str, icon: str,
                     monthlyBudget: float = 0.0) -> Tuple[bool, str]:
        """Add a new category."""
        error = _validate(name, color, icon, monthlyBudget)
        if error:
            return False, error
        name = name.strip()

        if self.get_category_by_name(name):
            return False, f"Category '{name}' already exists."

        try:
            perform_database_operation(
                """
                INSERT INTO Category (name, categoryTypeId, color, icon, monthlyBudget)
                VALUES (:name, :categoryTypeId, :color, :icon, :monthlyBudget)
                """,
                params={
                    "name": name,
                    "categoryTypeId": int(categoryTypeId),
                    "color": color,
                    "icon": icon,
                    "monthlyBudget": float(monthlyBudget or 0.0),
                },
            )
        except IntegrityViolation:
            # Lost a race with another insert, or the category type doesn't exist.
            return False, f"Could not add '{name}': duplicate name or unknown category type."

        logger.info("Category created (name length=%d).", len(name))
        return True, f"Category '{name}' added successfully."

    def update_category(self, id: int, name: str, categoryTypeId: int,
                        color: str, icon: str, monthlyBudget: float) -> Tuple[bool, str]:
        """Update an existing category."""
        error = _validate(name, color, icon, monthlyBudget)
        if error:
            return False, error
        name = name.strip()

        if not self.get_category_by_id(id):
            return False, f"Category with ID {id} not found."

        clash = fetch_query_results(
            "SELECT id FROM Category WHERE LOWER(name) = LOWER(:name) AND id <> :id",
            params={"name": name, "id": int(id)},
        )
        if not clash.empty:
            return False, f"Another category is already named '{name}'."

        try:
            perform_database_operation(
                """
                UPDATE Category
                SET name = :name,
                    categorytypeid = :categoryTypeId,
                    color = :color,
                    icon = :icon,
                    monthlyBudget = :monthlyBudget
                WHERE id = :id
                """,
                params={
                    "id": int(id),
                    "name": name,
                    "categoryTypeId": int(categoryTypeId),
                    "color": color,
                    "icon": icon,
                    "monthlyBudget": float(monthlyBudget or 0.0),
                },
            )
        except IntegrityViolation:
            return False, f"Could not update '{name}': duplicate name or unknown category type."

        logger.info("Category id=%s updated.", id)
        return True, f"Category '{name}' updated successfully."

    def get_usage(self, id: int) -> dict:
        """Count rows that reference this category (or its subcategories)."""
        result = fetch_query_results(
            """
            SELECT
              (SELECT COUNT(*) FROM BankTransaction
                 WHERE categoryid = :id
                    OR subcategoryid IN (SELECT id FROM SubCategory WHERE categoryid = :id)) AS transactions,
              (SELECT COUNT(*) FROM ClassificationRule
                 WHERE categoryid = :id
                    OR subcategoryid IN (SELECT id FROM SubCategory WHERE categoryid = :id)) AS rules,
              (SELECT COUNT(*) FROM MLTrainingSample
                 WHERE category_id = :id
                    OR sub_category_id IN (SELECT id FROM SubCategory WHERE categoryid = :id)) AS samples
            """,
            params={"id": int(id)},
        )
        row = result.iloc[0]
        return {k: int(row[k]) for k in ("transactions", "rules", "samples")}

    def remove_category(self, id: int) -> Tuple[bool, str]:
        """Remove a category and its subcategories atomically.

        Refuses (instead of failing half-way through) if transactions, rules or
        training samples still reference it. Its monthly budgets are removed with it.
        """
        if not self.get_category_by_id(id):
            return False, f"Category with ID {id} not found."

        usage = self.get_usage(id)
        blockers = [f"{n} {label}" for label, n in (
            ("transaction(s)", usage["transactions"]),
            ("classification rule(s)", usage["rules"]),
            ("training sample(s)", usage["samples"]),
        ) if n]
        if blockers:
            return False, "Cannot remove this category, it is still used by " + ", ".join(blockers) + "."

        params = {"id": int(id)}
        execute_statements([
            ("DELETE FROM Budget WHERE categoryid = :id", params),
            ("DELETE FROM SubCategory WHERE categoryid = :id", params),
            ("DELETE FROM Category WHERE id = :id", params),
        ])
        logger.info("Category id=%s and its subcategories removed.", id)
        return True, "Category and its subcategories removed successfully."