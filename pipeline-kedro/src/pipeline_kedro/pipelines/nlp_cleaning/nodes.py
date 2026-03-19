import pandas as pd
import re

def uniformize_posts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Uniformise le texte et les dates des posts pour préparer le ML.
    """
    # 1. Nettoyage basique du texte (minuscules, suppression liens HTTP)
    if "text" in df.columns:
        df["text_cleaned"] = df["text"].astype(str).str.lower()
        df["text_cleaned"] = df["text_cleaned"].apply(lambda x: re.sub(r'http\S+', '', x))
    
    # 2. Conversion de la date en format standard datetime
    if "createdAt" in df.columns:
        df["createdAt"] = pd.to_datetime(df["createdAt"])

    # 3. Retourne uniquement les colonnes utiles pour la suite du pipeline
    return df[["text_cleaned", "createdAt"]]