import streamlit as st
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score

@st.cache_resource
def get_trained_model(df: pd.DataFrame):
    if df.empty or "Description" not in df.columns or "Category" not in df.columns:
        return None, df
    
    clean = df.dropna(subset=["Description", "Category"])
    if len(clean) < 5:
        return None, df
    
    x_train = clean["Description"]
    y_train = clean["Category"]
    
    models = {
        "naive_bayes": make_pipeline(TfidfVectorizer(), MultinomialNB()),
        "random_forest": make_pipeline(TfidfVectorizer(), RandomForestClassifier(n_estimators=50)),
    }
    
    best_model = None
    best_score = 0
    
    for name, model in models.items():
        try:
            scores = cross_val_score(
                model,
                clean,
                y_train,
                cv=min(3, len(clean))
            )            
            if scores.mean() > best_score:
                best_score = scores.mean()
                best_model = model
        except Exception:
            continue
    
    if best_model:
        best_model.fit(x_train, y_train)
    
    return best_model, df
    

def predict_category(model, description):
    """Predict category using trained model."""
    if model is not None:  
        try:
            return model.predict([description])[0]
        except (ValueError, AttributeError):
            return "Others"
    return "Others"

def predict_with_confidence(model, description: str) -> tuple[str, float]:
    """Return prediction with confidence score."""
    if model is None:
        return "Others", 0.0
    
    try:
        probs = model.predict_proba([description])[0]
        max_prob = max(probs)
        if max_prob < 0.5:  # Low confidence
            return "Others", max_prob
        return model.predict([description])[0], max_prob
    except:
        return "Others", 0.0