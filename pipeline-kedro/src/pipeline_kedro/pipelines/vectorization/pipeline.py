"""
Pipeline 'vectorization'
generated using Kedro 1.0.0
"""

from kedro.pipeline import Node, Pipeline

from .nodes import vectorize_posts


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            Node(
                func=vectorize_posts,
                inputs=["cleaned_bluesky_posts", "params:vectorization"],
                outputs=["vectorized_posts", "tfidf_vectorizer"],
                name="vectorize_posts_node",
            ),
        ]
    )
