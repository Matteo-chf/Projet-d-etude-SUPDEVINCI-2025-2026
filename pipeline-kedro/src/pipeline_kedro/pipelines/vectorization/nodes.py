"""
Pipeline 'vectorization'
- Vectorise les posts Bluesky nettoyés avec TF-IDF
- Sauvegarde le vectorizer et la matrice de vecteurs
"""

import logging

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle

logger = logging.getLogger(__name__)


def vectorize_posts(cleaned_posts: pd.DataFrame, parameters: dict) -> tuple[pd.DataFrame, object]:
    """Vectorise le texte nettoyé des posts Bluesky avec TF-IDF.

    Args:
        cleaned_posts: DataFrame avec colonne 'cleaned_text'.
        parameters: Paramètres (max_features, ngram_range, min_df).
    Returns:
        Tuple (DataFrame avec vecteurs TF-IDF, vectorizer entraîné).
    """
    max_features = parameters.get("max_features", 5000)
    max_df = parameters.get("max_df", 0.95)
    min_df = parameters.get("min_df", 2)
    ngram_range = tuple(parameters.get("ngram_range", [1, 2]))

    logger.info(
        "Vectorisation TF-IDF : max_features=%d, ngram=%s, min_df=%s, max_df=%s",
        max_features, ngram_range, min_df, max_df,
    )

    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=ngram_range,
        min_df=min_df,
        max_df=max_df,
        sublinear_tf=True,
    )

    texts = cleaned_posts["cleaned_text"].tolist()
    tfidf_matrix = vectorizer.fit_transform(texts)

    # Convertir en DataFrame dense pour stockage Parquet
    feature_names = vectorizer.get_feature_names_out()
    vectors_df = pd.DataFrame(
        tfidf_matrix.toarray(),
        columns=feature_names,
    )

    # Conserver les métadonnées importantes
    vectors_df.insert(0, "uri", cleaned_posts["uri"].values)
    vectors_df.insert(1, "author_handle", cleaned_posts["author_handle"].values)
    vectors_df.insert(2, "cleaned_text", cleaned_posts["cleaned_text"].values)

    logger.info(
        "Vectorisation terminée : %d posts × %d features",
        vectors_df.shape[0], len(feature_names),
    )
    return vectors_df, vectorizer
