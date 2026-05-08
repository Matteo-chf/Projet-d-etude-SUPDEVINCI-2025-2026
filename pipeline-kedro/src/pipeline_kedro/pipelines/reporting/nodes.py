import os

import pandas as pd
from dotenv import find_dotenv, load_dotenv
from pymongo import MongoClient

load_dotenv(find_dotenv())


def print_report(raw_posts: pd.DataFrame) -> None:
    uri = os.getenv("MONGO_URI")
    client = MongoClient(uri)
    collection = client["Bluesky"]["timeline"]

    nb_imports = collection.count_documents({})

    total_tweets = 0
    for doc in collection.find({}, {"_id": 0, "post": 1, "data": 1, "record": 1, "author": 1}):
        if "post" in doc:
            total_tweets += 1
        elif "record" in doc and "author" in doc:
            total_tweets += 1
        elif "data" in doc:
            total_tweets += len(doc["data"].get("feed", []))

    print("=== Rapport Bluesky ===")
    print(f"Imports MongoDB  : {nb_imports}")
    print(f"Tweets en base   : {total_tweets}")
    print("======================")
