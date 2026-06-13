"""
Pipeline 'kmeans'
"""

from kedro.pipeline import Node, Pipeline

from .nodes import run_kmeans, save_to_postgres, score_reliability


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            Node(
                func=run_kmeans,
                inputs=["vectorized_posts", "params:kmeans"],
                outputs=["kmeans_results", "kmeans_model"],
                name="run_kmeans_node",
            ),
            Node(
                func=score_reliability,
                inputs=["kmeans_results", "params:kmeans"],
                outputs="scored_posts",
                name="score_reliability_node",
            ),
            Node(
                func=save_to_postgres,
                inputs=["scored_posts", "params:kmeans"],
                outputs=None,
                name="save_to_postgres_node",
            ),
        ]
    )
