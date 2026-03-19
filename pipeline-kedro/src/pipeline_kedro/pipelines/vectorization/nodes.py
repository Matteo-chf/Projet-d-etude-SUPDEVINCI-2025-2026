"""
Pipeline 'vectorization' — Nodes
Applique TF-IDF sur les posts Bluesky nettoyés.
"""

import logging
from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)


def vectorize_posts(
    df: pd.DataFrame, parameters: dict[str, Any]
) -> tuple[pd.DataFrame, TfidfVectorizer]:
    """
    Applique TF-IDF sur la colonne `text_cleaned` du DataFrame.

    Args:
        df: DataFrame contenant au minimum la colonne `text_cleaned`.
        parameters: Paramètres TF-IDF issus de `parameters_vectorization.yml`:
            - max_features (int): Nombre max de features.
            - max_df (float): Fréquence max (exclut les mots trop communs).
            - min_df (int|float): Fréquence min (exclut les mots trop rares).
            - ngram_range (list[int]): Plage de n-grams, ex. [1, 2].

    Returns:
        Tuple (tfidf_dataframe, vectorizer):
            - tfidf_dataframe: DataFrame dense (colonnes = termes TF-IDF).
            - vectorizer: L'objet TfidfVectorizer entraîné (à sauvegarder).
    """
    # Extraction des paramètres avec valeurs par défaut
    max_features = parameters.get("max_features", 5000)
    max_df = parameters.get("max_df", 0.95)
    min_df = parameters.get("min_df", 2)
    ngram_range = tuple(parameters.get("ngram_range", [1, 2]))

    logger.info(
        "Vectorisation TF-IDF : max_features=%d, max_df=%s, min_df=%s, ngram_range=%s",
        max_features,
        max_df,
        min_df,
        ngram_range,
    )

    # Nettoyage des valeurs manquantes
    texts = df["text_cleaned"].fillna("").astype(str)

    # Création et entraînement du vectorizer
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        max_df=max_df,
        min_df=min_df,
        ngram_range=ngram_range,
    )

    tfidf_matrix = vectorizer.fit_transform(texts)

    # Conversion sparse → dense DataFrame pour stockage Parquet
    feature_names = vectorizer.get_feature_names_out()
    tfidf_df = pd.DataFrame(
        tfidf_matrix.toarray(),
        columns=feature_names,
        index=df.index,
    )

    logger.info(
        "Matrice TF-IDF générée : %d documents × %d features",
        tfidf_df.shape[0],
        tfidf_df.shape[1],
    )

    return tfidf_df, vectorizer
