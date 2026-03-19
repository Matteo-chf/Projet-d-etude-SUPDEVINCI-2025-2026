"""
Pipeline 'vectorization' — Pipeline definition
Chaîne : bluesky_posts_uniformized → TF-IDF → tfidf_matrix + tfidf_vectorizer
"""

from kedro.pipeline import Pipeline, node

from .nodes import vectorize_posts


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                func=vectorize_posts,
                inputs=["bluesky_posts_uniformized", "params:vectorization"],
                outputs=["tfidf_matrix", "tfidf_vectorizer"],
                name="vectorize_tfidf_node",
            ),
        ]
    )
