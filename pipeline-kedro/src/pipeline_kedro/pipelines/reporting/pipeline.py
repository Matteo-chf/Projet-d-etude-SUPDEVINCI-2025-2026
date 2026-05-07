from kedro.pipeline import Node, Pipeline

from .nodes import print_report


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline([
        Node(
            func=print_report,
            inputs=["cleaned_bluesky_posts", "vectorized_posts"],
            outputs=None,
            name="print_report_node",
        ),
    ])
