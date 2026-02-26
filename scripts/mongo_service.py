import os
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class MongoService:
    def __init__(self, db_name="Bluesky"):
        uri = os.getenv("MONGO_URI")
        self.client = MongoClient(uri)
        self.db = self.client[db_name]

    def insert_timeline(self, data: dict):
        collection = self.db["timeline"]
        document = {
            "fetched_at": datetime.utcnow(),
            "data": data
        }
        return collection.insert_one(document).inserted_id
