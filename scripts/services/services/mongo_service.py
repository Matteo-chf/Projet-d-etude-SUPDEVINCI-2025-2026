from pymongo import MongoClient
from datetime import datetime
import os

class MongoService:
    def __init__(self):
        uri = os.getenv("MONGO_URI")
        self.client = MongoClient(uri)
        self.db = self.client["Bluesky"]

    def insert_timeline(self, items):
        if not items:
            return 0

        for item in items:
            item["inserted_at"] = datetime.utcnow()

        result = self.db.timeline.insert_many(items)
        return len(result.inserted_ids)

