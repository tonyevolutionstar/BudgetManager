import streamlit as st
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score

@st.cache_resource
def get_trained_model(df: pd.DataFrame):    
    """Train multiple models and select the best."""
    # Add multiple models
    models = {
        "naive_bayes": make_pipeline(TfidfVectorizer(), MultinomialNB()),
        "random_forest": make_pipeline(TfidfVectorizer(), RandomForestClassifier()),
    }
    
    # Cross-validate and select best
    best_model = None
    best_score = 0
    
    for name, model in models.items():
        scores = cross_val_score(model, x_train, y_train, cv=3)
        if scores.mean() > best_score:
            best_score = scores.mean()
            best_model = model
    
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