"""
Pipeline 'vectorization' — Vectorisation TF-IDF des posts Bluesky nettoyés.
Transforme la colonne `text_cleaned` en matrice de features numériques
exploitable par les modèles ML (clustering, classification).
"""

from .pipeline import create_pipeline  # noqa: F401

__all__ = ["create_pipeline"]
