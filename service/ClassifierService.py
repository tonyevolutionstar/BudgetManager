from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from data.database import DatabaseError
from src.repository.mlTrainingSampleRepository import MLTrainingSampleRepository

logger = logging.getLogger(__name__)

MAX_DESCRIPTION_LEN = 300   # longer descriptions are truncated before matching
MAX_PATTERN_LEN = 200       # ClassificationRule.Pattern is varchar(200)
MIN_ML_SAMPLES = 20
MIN_ML_CONFIDENCE = 0.55


@dataclass
class ClassificationResult:
    category: str
    sub_category: str | None
    confidence: float           # 0.0 - 1.0
    source: str                 # 'rule' | 'ml' | 'keyword' | 'unclassified'
    rule_id: int | None = None


# Category and subcategory names match DatabaseSchema.sql. None = no matching subcategory.
KEYWORD_MAP: dict[str, list[tuple[str, str | None]]] = {
    "Transportation": [
        ("cepsa", "Fuel"), ("galp", "Fuel"), ("bp", "Fuel"), ("repsol", "Fuel"), ("prio", "Fuel"),
        ("via verde", None), ("scut", None),
        ("parking", "Parking fee"), ("estacionamento", "Parking fee"),
        ("uber", None), ("bolt", None),
        ("cp", "Public Transport"), ("comboios", "Public Transport"),
        ("metro", "Public Transport"), ("carris", "Public Transport"),
    ],
    "Food": [
        ("continente", "Groceries"), ("pingo doce", "Groceries"), ("lidl", "Groceries"),
        ("aldi", "Groceries"), ("auchan", "Groceries"), ("mercadona", "Groceries"),
        ("intermarche", "Groceries"), ("froiz", "Groceries"),
        ("mcdonald", "Restaurants"), ("kfc", "Restaurants"), ("burger king", "Restaurants"),
        ("nando", "Restaurants"), ("restaurante", "Restaurants"),
        ("padaria", "Bakery"), ("pastelaria", "Coffee Shop"), ("cafe", "Coffee Shop"),
    ],
    "Housing": [
        ("epal", "Water"), ("indaqua", "Water"),
        ("edp", "Electricity and Gas"), ("endesa", "Electricity and Gas"), ("galp gas", "Electricity and Gas"),
        ("meo", "Internet"), ("nos", "Internet"), ("vodafone", "Internet"), ("nowo", "Internet"),
        ("renda", "Rent"), ("rent", "Rent"), ("condominio", "Condominium"),
    ],
    "Healthcare": [
        ("farmacia", "Pharmacy"), ("farma", "Pharmacy"), ("wells", "Pharmacy"),
        ("clinica", None), ("hospital", "Hospital"), ("dentist", "Dentist"), ("dentista", "Dentist"),
    ],
    "Subscriptions": [
        ("netflix", "Netflix"), ("spotify", "Spotify"), ("disney", "Disney"), ("hbo", "HBO"),
        ("amazon prime", "Prime"), ("youtube premium", "Youtube Premium"), ("apple.com", "Apple"),
    ],
    "Entertainment": [
        ("steam", "Games"), ("playstation", "Games"), ("xbox", "Games"),
        ("cinema", "Movies"), ("fnac", None), ("bertrand", None),
    ],
    "Personal": [
        ("zara", "Clothing"), ("h&m", "Clothing"), ("primark", "Clothing"),
        ("mango", "Clothing"), ("bershka", "Clothing"),
        ("gym", "Gym"), ("holmes", "Gym"), ("fitness", "Gym"),
        ("cabeleirei", "Haircut"), ("barber", "Haircut"),
    ],
    "Income": [
        ("salario", "Salary"), ("ordenado", "Salary"), ("vencimento", "Salary"),
        ("subsidio", None), ("reembolso", None), ("transferencia recebida", None),
    ],
    "Insurance": [
        ("seguro", "Health"), ("fidelidade", "Health"), ("allianz", "Health"),
        ("zurich", "Health"), ("generali", "Health"),
        ("comissao", None), ("anuidade", None),
    ],
    "Debt": [
        ("prestacao", "Credit Cards"), ("hipoteca", "Credit"),
    ],
}


def _normalise(text: str | None) -> str:
    """Lowercase, remove accents, collapse whitespace, cap the length."""
    text = (text or "").lower().strip()[:MAX_DESCRIPTION_LEN]
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", text)


def _keyword_pattern(keyword: str) -> re.Pattern:
    """Word-boundary pattern. Short keywords (<=3 chars) must be whole words;
    longer ones may be a word prefix ('mcdonald' matches 'mcdonalds')."""
    body = re.escape(keyword)
    tail = r"(?![a-z0-9])" if len(keyword) <= 3 else ""
    return re.compile(rf"(?<![a-z0-9]){body}{tail}")


# (compiled pattern, keyword length, category, subcategory), compiled once at import
_KEYWORD_PATTERNS: list[tuple[re.Pattern, int, str, str | None]] = [
    (_keyword_pattern(keyword), len(keyword), category, sub)
    for category, entries in KEYWORD_MAP.items()
    for keyword, sub in entries
]


# ---------------------------------------------------------------------------
# Layer 1: database rules
# ---------------------------------------------------------------------------

def _rule_value(rule: dict, *names: str, default=None):
    """First present key (PostgreSQL returns lowercase column names)."""
    for name in names:
        if name in rule and rule[name] is not None:
            return rule[name]
    return default


@lru_cache(maxsize=512)
def _compile_rule_regex(pattern: str) -> re.Pattern | None:
    if len(pattern) > MAX_PATTERN_LEN:
        logger.warning("Rule regex ignored: longer than %d characters.", MAX_PATTERN_LEN)
        return None
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error:
        logger.warning("Invalid regex in classification rule.")
        return None


def _classify_by_rules(description: str, rules: list[dict]) -> ClassificationResult | None:
    """Match against DB rules. Highest priority first, then longest pattern.

    Expected keys (case-insensitive column names from the repository query):
    pattern, matchtype/match_type, category_name, sub_category_name (optional),
    id, priority (optional, default 0), is_active (optional, default True).
    The ClassificationRule table has no category_name: the repository query must
    JOIN Category (and SubCategory) and alias the names.
    """
    norm = _normalise(description)

    def sort_key(rule: dict):
        return (_rule_value(rule, "priority", default=0), len(str(_rule_value(rule, "pattern", default=""))))

    for rule in sorted(rules, key=sort_key, reverse=True):
        if not _rule_value(rule, "is_active", "isactive", default=True):
            continue
        raw_pattern = str(_rule_value(rule, "pattern", default=""))
        if not raw_pattern:
            continue
        match_type = _rule_value(rule, "match_type", "matchtype", default="contains")

        if match_type == "regex":
            # Do NOT normalise a regex: it would change \D, \S, \W, ... into lowercase classes.
            compiled = _compile_rule_regex(raw_pattern)
            matched = bool(compiled and compiled.search(norm))
        else:
            pattern = _normalise(raw_pattern)
            if match_type == "starts_with":
                matched = norm.startswith(pattern)
            elif match_type == "exact":
                matched = norm == pattern
            else:  # 'contains'
                matched = pattern in norm

        if matched:
            return ClassificationResult(
                category=_rule_value(rule, "category_name", "categoryname"),
                sub_category=_rule_value(rule, "sub_category_name", "subcategoryname"),
                confidence=1.0,
                source="rule",
                rule_id=_rule_value(rule, "id"),
            )
    return None


# ---------------------------------------------------------------------------
# Layer 2: ML model
# ---------------------------------------------------------------------------

@st.cache_resource(max_entries=5)
def _build_ml_model(samples: tuple[tuple[str, str], ...]):
    """Train a TF-IDF + Logistic Regression pipeline on confirmed samples.

    Character n-grams (analyzer='char_wb') work better than word tokens for
    short, noisy bank descriptions. *samples* must be a hashable tuple so
    Streamlit can cache the result (at most 5 models are kept).
    """
    if len(samples) < MIN_ML_SAMPLES:
        logger.info("ML model: not enough samples (%d < %d), skipping training.", len(samples), MIN_ML_SAMPLES)
        return None

    texts = [_normalise(s[0]) for s in samples]
    labels = [s[1] for s in samples]
    if len(set(labels)) < 2:
        logger.info("ML model: samples contain a single category, skipping training.")
        return None

    model = make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=1, sublinear_tf=True),
        LogisticRegression(max_iter=1000, C=5.0, solver="lbfgs"),  # multinomial is the default
    )
    model.fit(texts, labels)
    logger.info("ML model trained on %d samples.", len(samples))
    return model


def _classify_by_ml(description: str, model, min_confidence: float = MIN_ML_CONFIDENCE) -> ClassificationResult | None:
    """Return a result if the model's confidence reaches the threshold."""
    if model is None:
        return None
    try:
        probs = model.predict_proba([_normalise(description)])[0]
        best = int(probs.argmax())
        if float(probs[best]) < min_confidence:
            return None
        return ClassificationResult(
            category=str(model.classes_[best]),
            sub_category=None,
            confidence=float(probs[best]),
            source="ml",
        )
    except Exception:
        logger.debug("ML classification failed", exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Layer 3: keywords
# ---------------------------------------------------------------------------

def _classify_by_keywords(description: str) -> ClassificationResult:
    """Longest matching keyword wins; 'Others' if nothing matches."""
    norm = _normalise(description)
    best: tuple[int, str, str | None] | None = None

    for pattern, length, category, sub in _KEYWORD_PATTERNS:
        if pattern.search(norm) and (best is None or length > best[0]):
            best = (length, category, sub)

    if best:
        return ClassificationResult(category=best[1], sub_category=best[2], confidence=0.75, source="keyword")
    return ClassificationResult(category="Others", sub_category=None, confidence=0.0, source="unclassified")


class TransactionClassifier:
    """Hybrid classifier: rules -> ML -> keywords -> unclassified."""

    def __init__(
        self,
        rules: list[dict] | None = None,
        training_samples: list[tuple[str, str]] | None = None,
    ):
        self._rules = rules or []
        self._ml = _build_ml_model(tuple(training_samples or []))

    def classify(self, description: str) -> ClassificationResult:
        """Classify a single transaction description through all layers."""
        return (
            _classify_by_rules(description, self._rules)
            or _classify_by_ml(description, self._ml)
            or _classify_by_keywords(description)
        )

    def classify_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Classify every row and return a copy with the result columns appended."""
        df = df.copy()
        results = [self.classify(d) for d in df["Description"].fillna("").astype(str)]

        df["Category"] = [r.category for r in results]
        df["SubCategory"] = [r.sub_category for r in results]
        df["ClassificationSource"] = [r.source for r in results]
        df["MLConfidence"] = [r.confidence for r in results]
        return df

    def predict_ml(self, description: str, min_confidence: float = MIN_ML_CONFIDENCE) -> ClassificationResult | None:
        """ML layer only (None when the model is not trained or not confident enough)."""
        return _classify_by_ml(description, self._ml, min_confidence)

    def add_feedback(
        self,
        description: str,
        correct_category: str,
        correct_sub: str | None = None,
        source: str = "manual",
    ) -> bool:
        """Persist a correction in MLTrainingSample so future runs learn from it.

        `source` is 'manual' (you changed the category), 'confirmed_rule' or 'confirmed_ml'
        (you accepted a suggestion). Returns True when it was saved. A new sample changes the
        sample tuple, which is the model cache key, so the next model is retrained automatically.
        Subcategories are not stored yet (correct_sub is ignored).
        """
        try:
            saved, _ = MLTrainingSampleRepository().add_samples([(description, correct_category, source)])
        except DatabaseError:
            logger.warning("Could not save the correction to MLTrainingSample.")
            return False
        return saved > 0


# ---------------------------------------------------------------------------
# Streamlit widget: inline correction in the transaction table
# ---------------------------------------------------------------------------

def render_correction_widget(
    classifier: TransactionClassifier,
    transaction: dict,
    available_categories: list[str],
    key: str | int | None = None,
) -> str | None:
    """Render a selectbox to correct one transaction's category.

    Pass a unique `key` (e.g. the row index or transaction id): two rows with the
    same description would otherwise raise DuplicateWidgetID. Returns the corrected
    category, or None if the user made no change.
    """
    current = transaction.get("Category", "Others")
    desc = transaction.get("Description", "")
    suffix = key if key is not None else hash(desc)

    col1, col2 = st.columns([3, 1])
    with col1:
        st.text(f"📝 {desc[:80]}")
    with col2:
        new_cat = st.selectbox(
            "Category",
            options=available_categories,
            index=available_categories.index(current) if current in available_categories else 0,
            key=f"corr_{suffix}",
            label_visibility="collapsed",
        )

    if new_cat != current and st.button("✅ Confirm", key=f"btn_{suffix}"):
        classifier.add_feedback(desc, new_cat)
        return new_cat

    return None