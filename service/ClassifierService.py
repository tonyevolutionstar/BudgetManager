from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass

import pandas as pd
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

logger = logging.getLogger(__name__)

@dataclass
class ClassificationResult:
    category: str
    sub_category: str | None
    confidence: float           # 0.0 – 1.0
    source: str                 # 'rule' | 'ml' | 'keyword' | 'unclassified'
    rule_id: int | None = None

KEYWORD_MAP: dict[str, list[tuple[str, str]]] = {
    "Transport": [
        ("cepsa",               "Fuel"),
        ("galp",                "Fuel"),
        ("bp ",                 "Fuel"),
        ("repsol",              "Fuel"),
        ("prio",                "Fuel"),
        ("via verde",           "Tolls"),
        ("scut",                "Tolls"),
        ("parking",             "Parking"),
        ("uber",                "Taxi / Rideshare"),
        ("bolt",                "Taxi / Rideshare"),
        ("cp ",                 "Train"),
        ("comboios",            "Train"),
        ("metro",               "Metro / Bus"),
        ("carris",              "Metro / Bus"),
    ],
    "Food & Groceries": [
        ("continente",          "Supermarket"),
        ("pingo doce",          "Supermarket"),
        ("lidl",                "Supermarket"),
        ("aldi",                "Supermarket"),
        ("auchan",              "Supermarket"),
        ("mercadona",           "Supermarket"),
        ("intermarche",         "Supermarket"),
        ("froiz",               "Supermarket"),
        ("mcdonald",            "Restaurant"),
        ("kfc",                 "Restaurant"),
        ("burger king",         "Restaurant"),
        ("nando",               "Restaurant"),
    ],
    "Housing": [
        ("epal",                "Water"),
        ("indaqua",             "Water"),
        ("edp",                 "Electricity"),
        ("endesa",              "Electricity"),
        ("galp gas",            "Gas"),
        ("meo",                 "Telecommunications"),
        ("nos ",                "Telecommunications"),
        ("vodafone",            "Telecommunications"),
        ("nowo",                "Telecommunications"),
        ("rent",                "Rent"),
        ("condominio",          "Condo Fee"),
    ],
    "Healthcare": [
        ("farmacia",            "Pharmacy"),
        ("farma",               "Pharmacy"),
        ("wells",               "Pharmacy"),
        ("clinica",             "Appointment"),
        ("hospital",            "Hospital"),
        ("dentist",             "Dentist"),
        ("multicare",           "Health Insurance"),
        ("advancecare",         "Health Insurance"),
        ("medicare",            "Health Insurance"),
    ],
    "Entertainment": [
        ("netflix",             "Streaming"),
        ("spotify",             "Streaming"),
        ("disney",              "Streaming"),
        ("hbo",                 "Streaming"),
        ("amazon prime",        "Streaming"),
        ("steam",               "Gaming"),
        ("playstation",         "Gaming"),
        ("cinema",              "Cinema"),
        ("fnac",                "Culture"),
        ("bertrand",            "Culture"),
    ],
    "Personal": [
        ("zara",                "Clothing"),
        ("h&m",                 "Clothing"),
        ("primark",             "Clothing"),
        ("mango",               "Clothing"),
        ("bershka",             "Clothing"),
        ("gym",                 "Gym"),
        ("holmes",              "Gym"),
        ("fitness",             "Gym"),
        ("cabeleirei",          "Beauty"),
        ("barber",              "Beauty"),
    ],
    "Income": [
        ("salario",             "Salary"),
        ("ordenado",            "Salary"),
        ("vencimento",          "Salary"),
        ("subsidio",            "Allowance"),
        ("reembolso",           "Refund"),
        ("transferencia recebida", "Incoming Transfer"),
    ],
    "Insurance": [
        ("seguro",              "Insurance"),
        ("fidelidade",          "Insurance"),
        ("allianz",             "Insurance"),
        ("zurich",              "Insurance"),
        ("generali",            "Insurance"),
    ],
    "Bank Fees": [
        ("comissao",            "Bank Commission"),
        ("anuidade",            "Credit Card Fee"),
        ("mbway",               "MB WAY"),
        ("multibanco",          "ATM"),
        ("prestacao",           "Loan Payment"),
        ("hipoteca",            "Mortgage"),
    ],
}

def _normalise(text: str) -> str:
    """Lowercase, remove accents, collapse whitespace."""
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text

def _classify_by_rules(description: str, rules: list[dict]) -> ClassificationResult | None:
    """Match description against DB rules (sorted by priority descending)."""
    norm = _normalise(description)

    for rule in sorted(rules, key=lambda r: r.get("priority", 0), reverse=True):
        if not rule.get("is_active", True):
            continue

        pattern    = _normalise(rule["pattern"])
        match_type = rule.get("match_type", "contains")

        matched = False
        if match_type == "contains":
            matched = pattern in norm
        elif match_type == "starts_with":
            matched = norm.startswith(pattern)
        elif match_type == "exact":
            matched = norm == pattern
        elif match_type == "regex":
            try:
                matched = bool(re.search(pattern, norm))
            except re.error:
                logger.warning("Invalid regex in rule id=%s: %s", rule.get("id"), pattern)

        if matched:
            return ClassificationResult(
                category=rule["category_name"],
                sub_category=rule.get("sub_category_name"),
                confidence=1.0,
                source="rule",
                rule_id=rule.get("id"),
            )
    return None

@st.cache_resource
def _build_ml_model(samples: tuple[tuple[str, str], ...]):
    """Train a TF-IDF + Logistic Regression pipeline on confirmed samples.

    Uses character n-grams (analyzer='char_wb') which work better than
    word tokens for short, noisy bank transaction descriptions.

    *samples* must be a hashable tuple so Streamlit can cache the result.
    """
    if len(samples) < 20:
        logger.info("ML model: not enough samples (%d < 20), skipping training.", len(samples))
        return None

    texts  = [s[0] for s in samples]
    labels = [s[1] for s in samples]

    model = make_pipeline(
        TfidfVectorizer(
            analyzer="char_wb",     # character n-grams — better for short strings
            ngram_range=(2, 4),     # bigrams to 4-grams
            min_df=1,
            sublinear_tf=True,
        ),
        LogisticRegression(
            max_iter=1000,
            C=5.0,
            multi_class="multinomial",
            solver="lbfgs",
        ),
    )
    model.fit(texts, labels)
    logger.info("ML model trained on %d samples.", len(samples))
    return model

def _classify_by_ml(description: str, model) -> ClassificationResult | None:
    """Return a ClassificationResult if the model confidence exceeds the threshold."""
    if model is None:
        return None
    try:
        norm  = _normalise(description)
        probs = model.predict_proba([norm])[0]
        max_p = float(max(probs))
        if max_p < 0.55:        # below this threshold the model is not confident enough
            return None
        cat = model.predict([norm])[0]
        return ClassificationResult(
            category=cat,
            sub_category=None,
            confidence=max_p,
            source="ml",
        )
    except Exception as e:
        logger.debug("ML classification failed: %s", e)
        return None

def _classify_by_keywords(description: str) -> ClassificationResult:
    """Match against the built-in KEYWORD_MAP; returns 'Others' if nothing matches."""
    norm     = _normalise(description)
    best_cat = best_sub = None
    best_len = 0

    for category, patterns in KEYWORD_MAP.items():
        for keyword, sub_category in patterns:
            if keyword in norm and len(keyword) > best_len:
                best_len = len(keyword)
                best_cat = category
                best_sub = sub_category

    if best_cat:
        return ClassificationResult(
            category=best_cat,
            sub_category=best_sub,
            confidence=0.75,
            source="keyword",
        )

    return ClassificationResult(
        category="Others",
        sub_category=None,
        confidence=0.0,
        source="unclassified",
    )


class TransactionClassifier:
    """Hybrid classifier: rules → ML → keywords → unclassified."""

    def __init__(
        self,
        rules: list[dict] | None = None,
        training_samples: list[tuple[str, str]] | None = None,
    ):
        self._rules = rules or []
        self._ml    = _build_ml_model(tuple(training_samples or []))

    def classify(self, description: str) -> ClassificationResult:
        """Classify a single transaction description through all three layers."""
        # Layer 1 — DB rules
        result = _classify_by_rules(description, self._rules)
        if result:
            return result

        # Layer 2 — ML model
        result = _classify_by_ml(description, self._ml)
        if result:
            return result

        # Layer 3 — keyword fallback
        return _classify_by_keywords(description)

    def classify_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Classify all rows in *df* and append result columns in-place."""
        df = df.copy()
        results = [self.classify(str(d)) for d in df.get("Description", [])]

        df["Category"]             = [r.category     for r in results]
        df["SubCategory"]          = [r.sub_category for r in results]
        df["ClassificationSource"] = [r.source       for r in results]
        df["MLConfidence"]         = [r.confidence   for r in results]
        return df

    def add_feedback(self, description: str, correct_category: str, correct_sub: str | None = None) -> None:
        """Record a manual correction for future retraining.

        In a full implementation this writes to the MLTrainingSample table
        and triggers a background retrain. Here it logs the correction so
        you can wire it up to your repository layer.
        """
        logger.info(
            "Feedback recorded: '%s' → %s / %s",
            description[:60], correct_category, correct_sub,
        )
        # TODO: MLTrainingSampleRepository.add(description, correct_category, correct_sub)
        # TODO: st.cache_resource.clear() to force model retrain on next request


# ─────────────────────────────────────────────────────────────────────────────
# Streamlit widget — inline correction in the transaction table
# ─────────────────────────────────────────────────────────────────────────────

def render_correction_widget(
    classifier: TransactionClassifier,
    transaction: dict,
    available_categories: list[str],
) -> str | None:
    """Render a selectbox to correct a single transaction's category.

    Returns the corrected category string, or None if the user made no change.
    """
    current = transaction.get("Category", "Others")
    desc    = transaction.get("Description", "")

    col1, col2 = st.columns([3, 1])
    with col1:
        st.text(f"📝 {desc[:80]}")
    with col2:
        new_cat = st.selectbox(
            "Category",
            options=available_categories,
            index=available_categories.index(current)
                  if current in available_categories else 0,
            key=f"corr_{hash(desc)}",
            label_visibility="collapsed",
        )

    if new_cat != current:
        if st.button("✅ Confirm", key=f"btn_{hash(desc)}"):
            classifier.add_feedback(desc, new_cat)
            return new_cat

    return None