from __future__ import annotations

import logging
import re
import unicodedata

import pandas as pd
import streamlit as st

from data.bankStatementExtractor import BankStatementExtractor
from data.database import DatabaseError
from service.ClassifierService import TransactionClassifier
from src.repository import CategoryRepository, MLTrainingSampleRepository

logger = logging.getLogger(__name__)

DEFAULT_CATEGORY = "Others"
MODES = ("uncategorised", "all")
CHANGE_COLUMNS = ["Row", "Date", "Description", "Current", "Suggested", "Confidence", "Matched"]
LEARNED = "learned"
ML_SUGGESTION_CONFIDENCE = 0.7     # stricter than the classifier's own 0.55: suggestions get applied in bulk
MIN_KEY_LENGTH = 4


# ---------------------------------------------------------------------------
# Known categories and the shared extractor
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def _db_category_names() -> list[str]:
    return [c["name"] for c in CategoryRepository().get_all_categories() if c.get("name")]


def get_extractor() -> BankStatementExtractor:
    if "extractor" not in st.session_state:
        st.session_state.extractor = BankStatementExtractor()
    return st.session_state.extractor


def get_known_categories(extractor: BankStatementExtractor | None = None) -> list[str]:
    """The app's categories from the database, or the extractor's own names if the DB is unavailable."""
    try:
        names = _db_category_names()
    except DatabaseError:
        logger.warning("Could not load categories from the database; using the extractor's names.")
        names = []
    return names or sorted((extractor or get_extractor()).categories)


def category_options(known: list[str], extractor: BankStatementExtractor | None = None) -> list[str]:
    """Everything a row may be assigned to: the app's categories plus the extractor's."""
    return sorted(set(known) | set((extractor or get_extractor()).categories))


# ---------------------------------------------------------------------------
# Learned samples (MLTrainingSample)
# ---------------------------------------------------------------------------

def memory_key(description) -> str:
    """Merchant-level fingerprint: lowercase, no accents, no digits or punctuation.

    'COMPRA CONTINENTE BRAGA 1234 05/01' and 'Compra Continente Braga 9876' share a key.
    Descriptions with fewer than 4 letters have no key (too ambiguous to memorise).
    """
    text = unicodedata.normalize("NFD", str(description or "").lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z]+", " ", text).strip()
    return text if len(text) >= MIN_KEY_LENGTH else ""


def build_memory(samples: list[tuple[str, str]]) -> dict[str, str]:
    """{memory_key: category}. `samples` must be oldest first: the latest correction overrides."""
    memory: dict[str, str] = {}
    for description, category in samples:
        key = memory_key(description)
        if key:
            memory[key] = category
    return memory


@st.cache_data(ttl=60)
def _db_samples() -> list[tuple[str, str]]:
    return [(r["description"], r["category"]) for r in MLTrainingSampleRepository().get_samples()]


def get_training_samples() -> list[tuple[str, str]]:
    """(description, category) pairs from MLTrainingSample, oldest first ([] if the DB is unavailable)."""
    try:
        return _db_samples()
    except DatabaseError:
        logger.warning("Could not load training samples.")
        return []


def get_learned() -> tuple[dict[str, str], TransactionClassifier | None]:
    """(memory, ml_classifier) built from the stored samples. ml_classifier is None without samples."""
    samples = get_training_samples()
    if not samples:
        return {}, None
    return build_memory(samples), TransactionClassifier(training_samples=samples)


def feedback_items(changes: pd.DataFrame, edited: pd.DataFrame) -> list[tuple[str, str, str]]:
    """What to save when the user applies the preview.

    `changes` is what was suggested, `edited` the table after the user's edits (same Row ids).
      edited category != suggested            -> 'manual'
      accepted keyword / rule suggestion       -> 'confirmed_rule'
      accepted ML suggestion                   -> 'confirmed_ml'
      accepted but without evidence ("Others" fallback) or already learned -> not saved
    """
    suggested = changes.set_index("Row")["Suggested"]
    items: list[tuple[str, str, str]] = []
    for row in edited.itertuples():
        if row.Suggested != suggested.get(row.Row):
            items.append((row.Description, row.Suggested, "manual"))
            continue
        evidence = str(row.Matched or "")
        if not evidence or evidence == LEARNED:
            continue
        items.append((row.Description, row.Suggested, "confirmed_ml" if evidence.startswith("ml") else "confirmed_rule"))
    return items


def save_feedback(items: list[tuple[str, str, str]]) -> tuple[int, int]:
    """Persist (description, category, source) triples. Returns (saved, skipped). Raises DatabaseError."""
    if not items:
        return 0, 0
    result = MLTrainingSampleRepository().add_samples(items)
    _db_samples.clear()          # the next suggestions must see what was just learned
    return result


def list_samples(limit: int = 200) -> pd.DataFrame:
    """The newest stored samples (fresh from the database), newest first, for the management table."""
    rows = MLTrainingSampleRepository().get_samples(limit)
    df = pd.DataFrame(rows, columns=["id", "description", "category", "source", "created_at"])
    return df.iloc[::-1].reset_index(drop=True)


def delete_samples(ids) -> int:
    deleted = MLTrainingSampleRepository().delete_samples(ids)
    _db_samples.clear()
    return deleted


# ---------------------------------------------------------------------------
# Suggest / apply
# ---------------------------------------------------------------------------

def suggest_categories(
    df: pd.DataFrame,
    known: list[str],
    mode: str = "uncategorised",
    extractor: BankStatementExtractor | None = None,
    memory: dict[str, str] | None = None,
    ml: TransactionClassifier | None = None,
) -> pd.DataFrame:
    """Table of the rows whose category would change.

    Columns: Row (position in df), Date, Description, Current, Suggested, Confidence, Matched.
    `Matched` is the evidence: 'learned', the matching keywords, or 'ml (0.82)'; empty when none.
    Pass the same df to apply_categories().
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    if df is None or df.empty:
        return pd.DataFrame(columns=CHANGE_COLUMNS)

    extractor = extractor or BankStatementExtractor()
    memory = memory or {}
    df = df.reset_index(drop=True)
    canonical = {name.lower(): name for name in known}
    fallback = canonical.get(DEFAULT_CATEGORY.lower(), DEFAULT_CATEGORY)

    descriptions = df["Description"].fillna("").astype(str)
    keyword_results = {d: extractor.categorise_transaction(d) for d in descriptions.unique()}   # repeated descriptions: once
    ml_results: dict[str, object] = {}
    current_values = df["Category"].fillna("").astype(str).str.strip()
    dates = df["Date"] if "Date" in df.columns else pd.Series([None] * len(df))

    def canon(name: str) -> str:
        return canonical.get(name.lower(), name)

    rows: list[dict] = []
    for i, (description, current) in enumerate(zip(descriptions, current_values)):
        known_current = canonical.get(current.lower())
        keyword = keyword_results[description]
        eligible = mode == "all" or known_current is None or known_current.lower() == DEFAULT_CATEGORY.lower()

        suggested, confidence, evidence = known_current, 0.0, ""
        if eligible:
            learned = memory.get(memory_key(description))
            if learned:
                suggested, confidence, evidence = canon(learned), 1.0, LEARNED
            elif keyword["keywords"]:
                suggested, confidence, evidence = canon(keyword["category"]), keyword["confidence"], ", ".join(keyword["keywords"])
            else:
                if ml is not None and description not in ml_results:
                    ml_results[description] = ml.predict_ml(description, ML_SUGGESTION_CONFIDENCE)
                prediction = ml_results.get(description)
                if prediction is not None:
                    suggested, confidence, evidence = canon(prediction.category), prediction.confidence, f"ml ({prediction.confidence:.2f})"
                else:
                    suggested = known_current or fallback

        if suggested != current:
            rows.append({
                "Row": i,
                "Date": dates.iloc[i],
                "Description": description,
                "Current": current,
                "Suggested": suggested,
                "Confidence": confidence,
                "Matched": evidence,
            })
    return pd.DataFrame(rows, columns=CHANGE_COLUMNS)


def apply_categories(df: pd.DataFrame, changes: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with the (possibly edited) suggestions written to Category."""
    out = df.reset_index(drop=True).copy()
    if changes is None or changes.empty:
        return out
    out["Category"] = out["Category"].astype(object)
    out.loc[changes["Row"].astype(int).to_numpy(), "Category"] = changes["Suggested"].to_numpy()
    return out


def auto_categorise(
    df: pd.DataFrame,
    known: list[str],
    mode: str = "uncategorised",
    extractor: BankStatementExtractor | None = None,
    memory: dict[str, str] | None = None,
    ml: TransactionClassifier | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """suggest + apply in one go. Returns (new_df, changes). Nothing is saved as a training sample."""
    changes = suggest_categories(df, known, mode, extractor, memory, ml)
    return apply_categories(df, changes), changes


def auto_categorise_session(mode: str = "uncategorised") -> int:
    """Categorise st.session_state.df in place, using what was learned. Returns the number of rows changed."""
    df = st.session_state.get("df")
    if df is None or df.empty:
        return 0
    extractor = get_extractor()
    memory, ml = get_learned()
    new_df, changes = auto_categorise(df, get_known_categories(extractor), mode, extractor, memory, ml)
    st.session_state.df = new_df
    st.session_state.model = None   # the transaction classifier retrains with the new categories
    if not changes.empty:
        from service.FileImporterService import save_dataframe
        try:
            save_dataframe(new_df)
        except OSError:
            logger.exception("Could not persist automatic categories")
            st.warning("Categories changed in this session, but the CSV could not be saved.")
    return len(changes)
