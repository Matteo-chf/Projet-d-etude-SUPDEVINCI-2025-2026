from kedro.pipeline import Node, Pipeline
from kedro.pipeline import Pipeline, node, pipeline
from .nodes import uniformize_posts 

from .nodes import (
    compare_passenger_capacity_exp,
    compare_passenger_capacity_go,
    create_confusion_matrix,
)


def create_pipeline(**kwargs) -> Pipeline:
    """This is a simple pipeline which generates a pair of plots"""
    return Pipeline(
        [
            Node(
                func=compare_passenger_capacity_exp,
                inputs="preprocessed_shuttles",
                outputs="shuttle_passenger_capacity_plot_exp",
            ),
            Node(
                func=compare_passenger_capacity_go,
                inputs="preprocessed_shuttles",
                outputs="shuttle_passenger_capacity_plot_go",
            ),
            Node(
                func=create_confusion_matrix,
                inputs="companies",
                outputs="dummy_confusion_matrix",
            ),
        ]
    )
 # On importe TA fonction de nettoyage

def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=uniformize_posts,           # La fonction dans nodes.py
                inputs="bluesky_posts_raw",      # Doit être dans catalog.yml
                outputs="bluesky_posts_uniformized", # Doit être dans catalog.yml
                name="uniformization_bluesky_node",
            ),
        ]
    )