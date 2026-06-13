"""
Pipeline 'kmeans'
- Applique K-Means sur les vecteurs TF-IDF
- Calcule la distance de chaque post au centroïde de son cluster
- Identifie les clusters dominés par des sources fiables
- Attribue un score de fiabilité à chaque post
- Sauvegarde les résultats dans PostgreSQL
"""

import logging
import os

import numpy as np
import pandas as pd
from dotenv import find_dotenv, load_dotenv
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize
from sqlalchemy import create_engine, text

load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

METADATA_COLS = ["uri", "author_handle", "cleaned_text"]


def run_kmeans(vectorized_posts: pd.DataFrame, parameters: dict) -> tuple[pd.DataFrame, object]:
    """Applique K-Means sur la matrice TF-IDF et calcule les distances aux centroïdes."""
    n_clusters = parameters.get("n_clusters", 20)
    random_state = parameters.get("random_state", 42)
    n_init = parameters.get("n_init", 10)

    feature_cols = [c for c in vectorized_posts.columns if c not in METADATA_COLS]
    X = vectorized_posts[feature_cols].values

    # Normalisation L2 : cosine distance devient distance euclidienne
    X_norm = normalize(X, norm="l2")

    logger.info("K-Means : n_clusters=%d sur %d posts x %d features", n_clusters, X_norm.shape[0], X_norm.shape[1])

    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=n_init)
    labels = kmeans.fit_predict(X_norm)

    # Distance euclidienne de chaque post au centroïde de son cluster
    centroids = kmeans.cluster_centers_
    distances = np.linalg.norm(X_norm - centroids[labels], axis=1)

    result = vectorized_posts[METADATA_COLS].copy()
    result["cluster"] = labels
    result["distance_to_centroid"] = distances

    logger.info("K-Means termine : %d clusters, distance moyenne=%.4f", n_clusters, distances.mean())
    return result, kmeans


def score_reliability(
    kmeans_results: pd.DataFrame,
    parameters: dict,
) -> pd.DataFrame:
    """
    Identifie les clusters fiables à partir des labels MongoDB (source_label=reliable)
    et attribue un score de fiabilité à chaque post.

    Score = 1 - (distance / max_distance_dans_cluster)
    Posts dans un cluster fiable → score entre 0 et 1
    Posts hors cluster fiable   → score = 0
    """
    from pymongo import MongoClient

    threshold = parameters.get("reliability_threshold", 0.5)

    # Récupérer les labels depuis MongoDB
    mongo_uri = os.getenv("MONGO_URI")
    client = MongoClient(mongo_uri)
    labeled = list(
        client["Bluesky"]["timeline"].find(
            {"source_label": "reliable"},
            {"_id": 0, "uri": 1},
        )
    )
    reliable_uris = {doc["uri"] for doc in labeled}
    logger.info("%d posts labelises 'reliable' recuperes depuis MongoDB", len(reliable_uris))

    # Identifier les clusters dominés par des sources fiables
    df = kmeans_results.copy()
    df["is_reliable_source"] = df["uri"].isin(reliable_uris)

    cluster_stats = df.groupby("cluster")["is_reliable_source"].agg(["sum", "count"])
    cluster_stats["reliable_ratio"] = cluster_stats["sum"] / cluster_stats["count"]
    reliable_clusters = set(cluster_stats[cluster_stats["reliable_ratio"] > 0].index)

    logger.info(
        "%d clusters sur %d contiennent au moins une source fiable",
        len(reliable_clusters), df["cluster"].nunique(),
    )

    # Normaliser la distance par cluster pour obtenir un score [0, 1]
    max_dist_per_cluster = df.groupby("cluster")["distance_to_centroid"].transform("max")
    df["reliability_score"] = 0.0

    in_reliable = df["cluster"].isin(reliable_clusters)
    df.loc[in_reliable, "reliability_score"] = (
        1 - df.loc[in_reliable, "distance_to_centroid"] / max_dist_per_cluster[in_reliable]
    ).clip(0, 1)

    df["reliability_label"] = "unknown"
    df.loc[df["reliability_score"] >= threshold, "reliability_label"] = "reliable"
    df.loc[(df["reliability_score"] < threshold) & (df["reliability_score"] > 0), "reliability_label"] = "suspect"

    logger.info(
        "Labels : reliable=%d | suspect=%d | unknown=%d",
        (df["reliability_label"] == "reliable").sum(),
        (df["reliability_label"] == "suspect").sum(),
        (df["reliability_label"] == "unknown").sum(),
    )

    return df


def save_to_postgres(scored_posts: pd.DataFrame, parameters: dict) -> None:
    """Sauvegarde les résultats dans PostgreSQL (table kmeans_results)."""
    pg_uri = os.getenv("POSTGRES_URI", "postgresql+psycopg2://airflow:airflow@localhost:5433/airflow")
    engine = create_engine(pg_uri)

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS kmeans_results (
                uri TEXT PRIMARY KEY,
                author_handle TEXT,
                cleaned_text TEXT,
                cluster INTEGER,
                distance_to_centroid FLOAT,
                reliability_score FLOAT,
                reliability_label TEXT,
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))

    # Upsert : mise à jour si uri existe déjà
    rows = scored_posts[
        ["uri", "author_handle", "cleaned_text", "cluster",
         "distance_to_centroid", "reliability_score", "reliability_label"]
    ].to_dict(orient="records")

    with engine.begin() as conn:
        for row in rows:
            conn.execute(text("""
                INSERT INTO kmeans_results
                    (uri, author_handle, cleaned_text, cluster, distance_to_centroid, reliability_score, reliability_label)
                VALUES
                    (:uri, :author_handle, :cleaned_text, :cluster, :distance_to_centroid, :reliability_score, :reliability_label)
                ON CONFLICT (uri) DO UPDATE SET
                    cluster = EXCLUDED.cluster,
                    distance_to_centroid = EXCLUDED.distance_to_centroid,
                    reliability_score = EXCLUDED.reliability_score,
                    reliability_label = EXCLUDED.reliability_label,
                    updated_at = NOW()
            """), row)

    logger.info("%d posts sauvegardes dans PostgreSQL (table kmeans_results)", len(rows))
