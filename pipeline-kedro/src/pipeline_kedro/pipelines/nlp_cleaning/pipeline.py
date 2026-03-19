"""
This is a boilerplate pipeline 'nlp_cleaning'
generated using Kedro 1.0.0
"""

from kedro.pipeline import Pipeline, node

from .nodes import uniformize_posts


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                func=uniformize_posts,
                inputs="bluesky_posts_raw",
                outputs="bluesky_posts_uniformized",
                name="uniformize_bluesky_posts_node",
            ),
        ]
    )
