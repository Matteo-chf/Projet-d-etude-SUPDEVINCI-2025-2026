"""
This is a boilerplate pipeline 'nlp_cleaning'
generated using Kedro 1.0.0
#pour clean les données textuelles
"""
import pandas as pd
import re

def uniformize_posts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Uniformise les colonnes et le texte pour le modèle ML.
    """
    # 1. Nettoyage basique du texte
    if "text" in df.columns:
        df["text_cleaned"] = df["text"].astype(str).str.lower()
        # Suppression des URLs
        df["text_cleaned"] = df["text_cleaned"].apply(lambda x: re.sub(r'http\S+', '', x))
    
    # 2. Gestion du format de date
    if "createdAt" in df.columns:
        df["createdAt"] = pd.to_datetime(df["createdAt"])

    # 3. Sélection des colonnes finales pour le catalogue
    return df[["text_cleaned", "createdAt"]]