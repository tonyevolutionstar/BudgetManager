from __future__ import annotations

import logging
from typing import Any, Sequence

import numpy as np
import pandas as pd
import streamlit as st
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Generic, user-safe database failure. Details are in the logs."""


class IntegrityViolation(DatabaseError):
    """A constraint (unique / foreign key / not null / check) was violated."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_native(value: Any) -> Any:
    """Convert NumPy / pandas scalars to types psycopg2 can adapt."""
    if value is pd.NaT:
        return None
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, float) and value != value:  # NaN -> NULL
        return None
    return value


def _sanitise_params(params: dict | None) -> dict:
    return {key: _to_native(val) for key, val in (params or {}).items()}


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def get_db_connection():
    """Return the Streamlit SQL connection (cached by Streamlit internally).

    pool_pre_ping avoids "SSL connection closed unexpectedly" errors when
    Neon suspends an idle compute. (kwargs are forwarded to create_engine;
    verify on your Streamlit version, or set it under [connections.neon].)
    """
    try:
        return st.connection("neon", type="sql", pool_pre_ping=True)
    except Exception as exc:
        logger.exception("Database connection error")
        raise DatabaseError("Could not connect to the database.") from exc


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def fetch_query_results(query: str, params: dict | None = None, ttl: int = 0) -> pd.DataFrame:
    """Execute a SELECT and return a DataFrame.

    ttl=0 disables Streamlit's result cache. SQLConnection.query() otherwise
    caches indefinitely, which made refresh_data() return stale rows.
    """
    conn = get_db_connection()
    try:
        return conn.query(query, params=_sanitise_params(params), ttl=ttl)
    except Exception as exc:
        logger.exception("Query execution error")
        raise DatabaseError("The database query failed.") from exc


def execute_statements(statements: Sequence[tuple[str, dict | None]]) -> list[int]:
    """Run INSERT/UPDATE/DELETE statements atomically in a single transaction.

    Returns the rowcount of each statement. If any statement fails, nothing
    is committed.
    """
    conn = get_db_connection()
    rowcounts: list[int] = []
    try:
        with conn.session as session:
            for query, params in statements:
                result = session.execute(text(query), _sanitise_params(params))
                rowcounts.append(result.rowcount)
            session.commit()
        return rowcounts
    except IntegrityError as exc:
        logger.warning("Integrity violation: %s", exc.orig)
        raise IntegrityViolation("The operation violates a database constraint.") from exc
    except Exception as exc:
        logger.exception("Database operation error")
        raise DatabaseError("The database operation failed.") from exc


def perform_database_operation(query: str, params: dict | None = None) -> int:
    """Execute a single INSERT / UPDATE / DELETE and return its rowcount."""
    return execute_statements([(query, params)])[0]


def get_table_columns(table_name: str) -> list[str]:
    """Return the column names of a table in the current schema."""
    query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND LOWER(table_name) = LOWER(:table_name)
        ORDER BY ordinal_position
    """
    df = fetch_query_results(query, params={"table_name": table_name}, ttl=3600)
    return list(df["column_name"]) if not df.empty else []