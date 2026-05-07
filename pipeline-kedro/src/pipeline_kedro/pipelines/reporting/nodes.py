import pandas as pd


def print_report(cleaned_posts: pd.DataFrame, vectorized_posts: pd.DataFrame) -> None:
    print("=== Rapport pipeline Bluesky ===")
    print(f"Posts nettoyes     : {len(cleaned_posts)}")
    print(f"Posts vectorises   : {len(vectorized_posts)}")
    print(f"Features TF-IDF    : {len(vectorized_posts.columns) - 3}")
    print("================================")
