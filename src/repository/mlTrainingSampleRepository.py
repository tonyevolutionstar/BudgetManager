import logging
import re
from collections.abc import Iterable, Sequence

from data.database import execute_statements, fetch_query_results, to_records

logger = logging.getLogger(__name__)

ALLOWED_SOURCES = ("manual", "confirmed_ml", "confirmed_rule")
MAX_DESCRIPTION = 300


class MLTrainingSampleRepository:
    """Labelled descriptions the app learns from (table MLTrainingSample).

    source:
      manual          you changed the suggested category
      confirmed_rule  you accepted a keyword / rule suggestion
      confirmed_ml    you accepted a suggestion made by the ML model
    Requires the unique index uq_ml_sample (DatabaseSchema.sql / migrations/003).
    """

    def add_samples(self, samples: Iterable[tuple[str, str, str]]) -> tuple[int, int]:
        """Save (description, category_name, source) triples in ONE transaction.

        Saving the same description for the same category again refreshes its timestamp.
        Returns (saved, skipped); a sample is skipped when the description is empty or the
        category name does not exist in the database.
        """
        samples = list(samples)
        statements = []
        for description, category, source in samples:
            if source not in ALLOWED_SOURCES:
                raise ValueError(f"source must be one of {ALLOWED_SOURCES}")
            description = re.sub(r"\s+", " ", str(description or "")).strip()[:MAX_DESCRIPTION]
            if not description or not category:
                continue
            statements.append((
                """
                INSERT INTO MLTrainingSample (description, categoryid, source)
                SELECT :description, c.id, :source FROM Category c WHERE LOWER(c.name) = LOWER(:category)
                ON CONFLICT (md5(lower(description)), categoryid)
                DO UPDATE SET created_at = NOW(), source = EXCLUDED.source
                """,
                {"description": description, "category": str(category), "source": source},
            ))
        if not statements:
            return 0, len(samples)

        saved = sum(1 for count in execute_statements(statements) if count)
        return saved, len(samples) - saved

    def get_samples(self, limit: int | None = 5000) -> list[dict]:
        """Samples oldest first (so the latest correction overrides earlier ones when replayed).

        With a limit, the NEWEST `limit` samples are returned. Keys: id, description, category,
        sub_category, source, created_at.
        """
        base = """
            SELECT s.id, s.description, c.name AS category, sc.name AS sub_category, s.source, s.created_at
            FROM MLTrainingSample s
            JOIN Category c ON c.id = s.categoryid
            LEFT JOIN SubCategory sc ON sc.id = s.sub_categoryid
        """
        if limit is None:
            query, params = base + " ORDER BY s.created_at, s.id", {}
        else:
            query = f"SELECT * FROM ({base} ORDER BY s.created_at DESC, s.id DESC LIMIT :limit) t ORDER BY created_at, id"
            params = {"limit": int(limit)}
        result = fetch_query_results(query, params=params)
        return [] if result.empty else to_records(result)

    def count(self) -> int:
        return int(fetch_query_results("SELECT COUNT(*) AS n FROM MLTrainingSample").iloc[0]["n"])

    def delete_samples(self, ids: Sequence[int]) -> int:
        """Forget samples by id. Returns how many were deleted."""
        ids = [int(i) for i in ids]
        if not ids:
            return 0
        return execute_statements([("DELETE FROM MLTrainingSample WHERE id = ANY(:ids)", {"ids": ids})])[0]