"""
Pipeline 'credibility' — Méthode : MiniLM + K-Means + similarité cosinus

Approche (détection d'anomalie / one-class) :
  1. generate_embeddings   : encode chaque post en vecteur MiniLM 384 dims
  2. train_reliable_clusters : K-Means entraîné UNIQUEMENT sur les posts "reliable"
                               → apprend les "formes" du contenu fiable
  3. score_by_cluster_distance : score = similarité cosinus au centroïde le plus proche
                                 Post proche d'un cluster fiable → score élevé
                                 Post éloigné de tous les clusters → score bas
  4. save_credibility_to_postgres : persistence PostgreSQL

Avantage par rapport à la Logistic Regression binaire :
  - Aucun besoin d'exemples "unreliable" (quasi absents sur Bluesky)
  - Le modèle apprend uniquement la distribution du contenu fiable
  - Tout contenu sémantiquement éloigné reçoit automatiquement un score bas
"""

import logging
import os

import numpy as np
import pandas as pd
from dotenv import find_dotenv, load_dotenv
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize
from sqlalchemy import create_engine, text

load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

METADATA_COLS = ["uri", "author_handle", "cleaned_text"]


def generate_embeddings(cleaned_posts: pd.DataFrame, parameters: dict) -> pd.DataFrame:
    """
    Encode chaque article en vecteur sémantique 384 dimensions.
    Utilise paraphrase-multilingual-MiniLM-L12-v2 (multilingue, léger).
    """
    model_name = parameters.get("model_name", "paraphrase-multilingual-MiniLM-L12-v2")
    batch_size = parameters.get("batch_size", 32)

    logger.info("Chargement du modèle d'embedding : %s", model_name)
    encoder = SentenceTransformer(model_name)

    texts = cleaned_posts["cleaned_text"].tolist()
    logger.info("Encodage de %d articles (batch_size=%d)...", len(texts), batch_size)

    embeddings = encoder.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
    )

    embedding_cols = [f"emb_{i}" for i in range(embeddings.shape[1])]
    df_embeddings = pd.DataFrame(embeddings, columns=embedding_cols)

    result = pd.concat(
        [cleaned_posts[METADATA_COLS].reset_index(drop=True), df_embeddings],
        axis=1,
    )

    logger.info("Embeddings générés : shape=%s", result.shape)
    return result


def train_reliable_clusters(
    embedded_posts: pd.DataFrame,
    parameters: dict,
) -> dict:
    """
    Entraîne un K-Means sur les embeddings des posts "reliable" uniquement.

    Retourne un dict contenant :
      - "kmeans"  : le modèle K-Means (centroids des clusters fiables)
      - "p5_sim"  : 5e percentile des similarités cosinus des posts fiables
                    → seuil bas de normalisation (posts en dessous = score 0)

    Principe de scoring (voir score_by_cluster_distance) :
      score = (sim_cosinus - p5_sim) / (1 - p5_sim), clipé dans [0, 1]
    """
    from pymongo import MongoClient

    n_clusters = parameters.get("n_clusters", 10)

    # Récupère les URIs des posts "reliable" depuis MongoDB
    mongo_uri = os.getenv("MONGO_URI")
    client = MongoClient(mongo_uri)
    reliable_uris = {
        doc["uri"]
        for doc in client["Bluesky"]["timeline"].find(
            {"source_label": "reliable"}, {"_id": 0, "uri": 1}
        )
    }
    client.close()

    logger.info("%d URIs 'reliable' récupérées depuis MongoDB.", len(reliable_uris))

    # Filtrer embedded_posts pour ne garder que les posts fiables
    df_rel = embedded_posts[embedded_posts["uri"].isin(reliable_uris)]

    if len(df_rel) < n_clusters:
        raise ValueError(
            f"Pas assez de posts fiables ({len(df_rel)}) pour {n_clusters} clusters. "
            "Réduisez n_clusters ou enrichissez la collecte."
        )

    feat_cols = [c for c in embedded_posts.columns if c.startswith("emb_")]
    X = df_rel[feat_cols].values

    # Normalisation L2 : rend la distance euclidienne équivalente à la distance cosinus.
    # Les centroids K-Means sont ainsi dans le même espace que les similarités cosinus.
    X_norm = normalize(X)

    logger.info(
        "Entraînement K-Means sur %d posts fiables (n_clusters=%d)...",
        len(df_rel), n_clusters,
    )
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    kmeans.fit(X_norm)

    # Calcule la similarité cosinus de chaque post fiable à son centroïde le plus proche.
    # On sauvegarde p5 (seuil bas) et p95 (seuil haut) pour normaliser :
    #   [p5, p95] → [0, 1]  : les posts fiables typiques atterrissent autour de 50 %
    sims = cosine_similarity(X_norm, kmeans.cluster_centers_).max(axis=1)
    p5_sim  = float(np.percentile(sims, 5))
    mean_sim = float(np.mean(sims))

    logger.info(
        "Similarités cosinus (posts fiables → centroïde) : "
        "min=%.3f | p5=%.3f | mean=%.3f | max=%.3f",
        sims.min(), p5_sim, mean_sim, sims.max(),
    )

    # La normalisation ancore la moyenne des posts fiables à 70 % (score "reliable" typique).
    # score = 0.7 * (raw - p5) / (mean - p5)   pour raw ≤ mean
    # score = 0.7 + 0.3 * (raw - mean) / (1 - mean)  pour raw > mean
    # Résultat : p5 → 0 % | mean → 70 % | 1.0 → 100 %
    return {"kmeans": kmeans, "p5_sim": p5_sim, "mean_sim": mean_sim}


def score_by_cluster_distance(
    embedded_posts: pd.DataFrame,
    credibility_model: dict,
    parameters: dict,
) -> pd.DataFrame:
    """
    Attribue un score de crédibilité à chaque article selon sa proximité
    aux clusters de contenu fiable.

    score = (sim_cosinus_max - p5_sim) / (1 - p5_sim), clipé dans [0.0, 1.0]

    - sim_cosinus_max : similarité au centroïde le plus proche
    - p5_sim          : seuil bas calibré sur les posts fiables (5e percentile)

    Plus le texte est sémantiquement proche du contenu fiable → score proche de 1.
    Plus il s'en éloigne → score proche de 0.
    """
    threshold = parameters.get("reliability_threshold", 0.6)

    kmeans   = credibility_model["kmeans"]
    p5_sim   = credibility_model["p5_sim"]
    mean_sim = credibility_model["mean_sim"]

    feat_cols = [c for c in embedded_posts.columns if c.startswith("emb_")]
    X = embedded_posts[feat_cols].values
    X_norm = normalize(X)

    logger.info("Scoring de %d articles par distance aux clusters fiables...", len(X))

    # Similarité cosinus à chaque centroïde → on garde la plus haute (cluster le plus proche)
    raw_sims = cosine_similarity(X_norm, kmeans.cluster_centers_).max(axis=1)

    # Normalisation piecewise ancrée sur la moyenne des posts fiables = 70 % :
    #   raw ≤ mean : score = 0.7 * (raw - p5) / (mean - p5)
    #   raw > mean : score = 0.7 + 0.3 * (raw - mean) / (1.0 - mean)
    low  = np.where(raw_sims <= mean_sim,
                    0.7 * (raw_sims - p5_sim) / max(mean_sim - p5_sim, 1e-9),
                    0.7 + 0.3 * (raw_sims - mean_sim) / max(1.0 - mean_sim, 1e-9))
    scores = np.clip(low, 0.0, 1.0).round(4)

    df = embedded_posts[METADATA_COLS].copy()
    df["credibility_score"] = scores
    df["credibility_label"] = "suspect"
    df.loc[df["credibility_score"] >= threshold, "credibility_label"] = "reliable"
    df.loc[df["credibility_score"] < (1.0 - threshold), "credibility_label"] = "unreliable"

    logger.info(
        "Scoring terminé → reliable=%d | suspect=%d | unreliable=%d",
        (df["credibility_label"] == "reliable").sum(),
        (df["credibility_label"] == "suspect").sum(),
        (df["credibility_label"] == "unreliable").sum(),
    )

    return df


def save_credibility_to_postgres(credibility_scores: pd.DataFrame, parameters: dict) -> None:
    """Sauvegarde les scores de crédibilité dans PostgreSQL (table credibility_results)."""
    pg_uri = os.getenv("POSTGRES_URI", "postgresql+psycopg2://airflow:airflow@localhost:5433/airflow")
    engine = create_engine(pg_uri)

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS credibility_results (
                uri TEXT PRIMARY KEY,
                author_handle TEXT,
                cleaned_text TEXT,
                credibility_score FLOAT,
                credibility_label TEXT,
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))

    rows = credibility_scores[
        ["uri", "author_handle", "cleaned_text", "credibility_score", "credibility_label"]
    ].to_dict(orient="records")

    with engine.begin() as conn:
        for row in rows:
            conn.execute(text("""
                INSERT INTO credibility_results
                    (uri, author_handle, cleaned_text, credibility_score, credibility_label)
                VALUES
                    (:uri, :author_handle, :cleaned_text, :credibility_score, :credibility_label)
                ON CONFLICT (uri) DO UPDATE SET
                    credibility_score = EXCLUDED.credibility_score,
                    credibility_label = EXCLUDED.credibility_label,
                    updated_at = NOW()
            """), row)

    logger.info("%d articles sauvegardés dans PostgreSQL (table credibility_results)", len(rows))
