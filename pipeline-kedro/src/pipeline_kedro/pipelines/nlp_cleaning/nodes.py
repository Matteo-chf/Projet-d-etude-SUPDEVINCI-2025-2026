import os
import re

import pandas as pd
from dotenv import find_dotenv, load_dotenv
from pymongo import MongoClient

load_dotenv(find_dotenv())


def fetch_from_mongo() -> pd.DataFrame:
    uri = os.getenv("MONGO_URI")
    client = MongoClient(uri)
    docs = list(client["Bluesky"]["timeline"].find({}, {"_id": 0}))

    records = []
    for doc in docs:
        post = doc.get("post", {})
        record = post.get("record", {})
        author = post.get("author", {})
        text = record.get("text", "")
        if text:
            records.append({
                "uri": post.get("uri", ""),
                "author_handle": author.get("handle", ""),
                "created_at": record.get("createdAt", ""),
                "raw_text": text,
            })

    return pd.DataFrame(records)


def clean_posts(raw_posts: pd.DataFrame) -> pd.DataFrame:
    def clean_text(text: str) -> str:
        text = text.lower()
        text = re.sub(r"http\S+|www\S+", "", text)
        text = re.sub(r"@\w+", "", text)
        text = re.sub(r"#\w+", "", text)
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    df = raw_posts.copy()
    df["cleaned_text"] = df["raw_text"].apply(clean_text)
    df = df[df["cleaned_text"].str.len() > 0]
    return df[["uri", "author_handle", "created_at", "cleaned_text"]]
