from kedro.pipeline import Node, Pipeline

from .nodes import print_report


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline([
        Node(
            func=print_report,
            inputs="raw_bluesky_posts",
            outputs=None,
            name="print_report_node",
        ),
    ])
