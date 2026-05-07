from kedro.pipeline import Node, Pipeline

from .nodes import clean_posts, fetch_from_mongo


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline([
        Node(
            func=fetch_from_mongo,
            inputs=None,
            outputs="raw_bluesky_posts",
            name="fetch_from_mongo_node",
        ),
        Node(
            func=clean_posts,
            inputs="raw_bluesky_posts",
            outputs="cleaned_bluesky_posts",
            name="clean_posts_node",
        ),
    ])
