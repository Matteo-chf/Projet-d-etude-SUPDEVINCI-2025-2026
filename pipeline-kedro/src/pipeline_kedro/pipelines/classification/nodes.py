"""
Pipeline 'classification'
- Calcule des features emotionnelles (VADER) sur le texte nettoye
- Entraine un classifieur scikit-learn (baseline) sur les labels reliable/unreliable
- Attribue un score de vraisemblance ("reliability_score") a chaque post
- Sauvegarde les resultats dans PostgreSQL
"""

import logging
import os

import numpy as np
import pandas as pd
from dotenv import find_dotenv, load_dotenv
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sqlalchemy import create_engine, text
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

METADATA_COLS = ["uri", "author_handle", "cleaned_text", "source_label"]

_analyzer = SentimentIntensityAnalyzer()


def add_emotion_features(vectorized_posts: pd.DataFrame) -> pd.DataFrame:
    """Ajoute des scores d'intensite emotionnelle (VADER) calcules sur le texte nettoye.

    Les fake news ont souvent une charge emotionnelle plus marquee
    (registre alarmiste, indignation) que la presse fiable.
    """
    df = vectorized_posts.copy()
    scores = df["cleaned_text"].apply(_analyzer.polarity_scores)
    df["emotion_neg"] = scores.apply(lambda s: s["neg"])
    df["emotion_neu"] = scores.apply(lambda s: s["neu"])
    df["emotion_pos"] = scores.apply(lambda s: s["pos"])
    df["emotion_compound"] = scores.apply(lambda s: s["compound"])

    logger.info("Features emotionnelles calculees pour %d posts", len(df))
    return df


def fetch_labels_from_mongo() -> pd.DataFrame:
    """Recupere les labels reliable/unreliable depuis MongoDB."""
    from pymongo import MongoClient

    mongo_uri = os.getenv("MONGO_URI")
    client = MongoClient(mongo_uri)
    docs = list(
        client["Bluesky"]["timeline"].find(
            {"source_label": {"$in": ["reliable", "unreliable"]}},
            {"_id": 0, "uri": 1, "source_label": 1},
        )
    )
    logger.info("%d posts labelises (reliable/unreliable) recuperes depuis MongoDB", len(docs))
    return pd.DataFrame(docs, columns=["uri", "source_label"])


def train_classifier(
    posts_with_emotion: pd.DataFrame,
    source_labels: pd.DataFrame,
    parameters: dict,
) -> tuple[pd.DataFrame, object]:
    """Entraine un classifieur baseline (regression logistique) sur TF-IDF + emotion.

    Retourne le score de vraisemblance ("reliability_score") pour TOUS les posts
    (pas seulement les posts labelises), et le modele entraine.
    """
    test_size = parameters.get("test_size", 0.2)
    random_state = parameters.get("random_state", 42)
    class_weight = parameters.get("class_weight", "balanced")

    merged = posts_with_emotion.merge(source_labels, on="uri", how="left")
    labeled = merged[merged["source_label"].isin(["reliable", "unreliable"])]

    if labeled["source_label"].nunique() < 2:
        raise ValueError(
            "Il faut au moins des exemples 'reliable' ET 'unreliable' pour entrainer le classifieur."
        )

    feature_cols = [c for c in merged.columns if c not in METADATA_COLS]

    X_labeled = labeled[feature_cols].values
    y_labeled = (labeled["source_label"] == "reliable").astype(int)

    logger.info(
        "Entrainement sur %d posts labelises (%d reliable / %d unreliable)",
        len(labeled), y_labeled.sum(), (1 - y_labeled).sum(),
    )

    X_train, X_test, y_train, y_test = train_test_split(
        X_labeled, y_labeled,
        test_size=test_size, random_state=random_state, stratify=y_labeled,
    )

    model = LogisticRegression(class_weight=class_weight, max_iter=1000)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred, target_names=["unreliable", "reliable"])
    logger.info("Rapport de classification (jeu de test) :\n%s", report)

    proba_reliable = model.predict_proba(merged[feature_cols].values)[:, 1]

    result = merged[["uri", "author_handle", "cleaned_text", "source_label"]].copy()
    result["reliability_score"] = proba_reliable
    result["predicted_label"] = np.where(proba_reliable >= 0.5, "reliable", "unreliable")

    return result, model


def save_to_postgres(classification_results: pd.DataFrame, parameters: dict) -> None:
    """Sauvegarde les resultats dans PostgreSQL (table classification_results)."""
    pg_uri = os.getenv("POSTGRES_URI", "postgresql+psycopg2://airflow:airflow@localhost:5433/airflow")
    engine = create_engine(pg_uri)

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS classification_results (
                uri TEXT PRIMARY KEY,
                author_handle TEXT,
                cleaned_text TEXT,
                source_label TEXT,
                reliability_score FLOAT,
                predicted_label TEXT,
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))

    rows = classification_results[
        ["uri", "author_handle", "cleaned_text", "source_label", "reliability_score", "predicted_label"]
    ].to_dict(orient="records")

    with engine.begin() as conn:
        for row in rows:
            conn.execute(text("""
                INSERT INTO classification_results
                    (uri, author_handle, cleaned_text, source_label, reliability_score, predicted_label)
                VALUES
                    (:uri, :author_handle, :cleaned_text, :source_label, :reliability_score, :predicted_label)
                ON CONFLICT (uri) DO UPDATE SET
                    source_label = EXCLUDED.source_label,
                    reliability_score = EXCLUDED.reliability_score,
                    predicted_label = EXCLUDED.predicted_label,
                    updated_at = NOW()
            """), row)

    logger.info("%d posts sauvegardes dans PostgreSQL (table classification_results)", len(rows))
