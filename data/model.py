import streamlit as st
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

@st.cache_resource
def get_trained_model(df: pd.DataFrame):
    """Train and return model + DataFrame, or (None, None) if no data."""
    if df is None or df.empty or "Description" not in df.columns or "Category" not in df.columns:
        return None, df
    
    # Remove rows with empty description or category
    train_df = df.dropna(subset=["Description", "Category"])
    train_df = train_df[train_df["Description"].str.strip() != ""]
    
    if train_df.empty:
        return None, df
    
    # Train pipeline
    pipeline = make_pipeline(TfidfVectorizer(), MultinomialNB())
    pipeline.fit(train_df["Description"], train_df["Category"])
    
    return pipeline, df

def predict_category(model, description):
    """Predict category using trained model."""
    if model is not None:  
        try:
            return model.predict([description])[0]
        except (ValueError, AttributeError):
            return "Others"
    return "Others"