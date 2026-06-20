"""
Pipeline 'credibility' — MiniLM + K-Means (détection d'anomalie)
"""

from kedro.pipeline import Node, Pipeline

from .nodes import (
    generate_embeddings,
    save_credibility_to_postgres,
    score_by_cluster_distance,
    train_reliable_clusters,
)


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            Node(
                func=generate_embeddings,
                inputs=["cleaned_bluesky_posts", "params:credibility"],
                outputs="embedded_posts",
                name="generate_embeddings_node",
            ),
            Node(
                func=train_reliable_clusters,
                inputs=["embedded_posts", "params:credibility"],
                outputs="credibility_model",
                name="train_reliable_clusters_node",
            ),
            Node(
                func=score_by_cluster_distance,
                inputs=["embedded_posts", "credibility_model", "params:credibility"],
                outputs="credibility_scores",
                name="score_by_cluster_distance_node",
            ),
            Node(
                func=save_credibility_to_postgres,
                inputs=["credibility_scores", "params:credibility"],
                outputs=None,
                name="save_credibility_to_postgres_node",
            ),
        ]
    )
