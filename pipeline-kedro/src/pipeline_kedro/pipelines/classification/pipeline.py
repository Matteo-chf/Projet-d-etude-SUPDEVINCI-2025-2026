"""
Pipeline 'classification'
"""

from kedro.pipeline import Node, Pipeline

from .nodes import add_emotion_features, fetch_labels_from_mongo, save_to_postgres, train_classifier


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            Node(
                func=fetch_labels_from_mongo,
                inputs=None,
                outputs="source_labels",
                name="fetch_labels_from_mongo_node",
            ),
            Node(
                func=add_emotion_features,
                inputs="vectorized_posts",
                outputs="posts_with_emotion",
                name="add_emotion_features_node",
            ),
            Node(
                func=train_classifier,
                inputs=["posts_with_emotion", "source_labels", "params:classification"],
                outputs=["classification_results", "classifier_model"],
                name="train_classifier_node",
            ),
            Node(
                func=save_to_postgres,
                inputs=["classification_results", "params:classification"],
                outputs=None,
                name="save_classification_to_postgres_node",
            ),
        ]
    )
