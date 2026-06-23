from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

class MongoService:
    def __init__(self):
        uri = os.getenv("MONGO_URI")
        self.client = MongoClient(uri)
        self.db = self.client["Bluesky"]

    def insert_timeline(self, items):
        # Upsert sur "uri" : ignore silencieusement les doublons deja en base
        if not items:
            return 0

        from pymongo import UpdateOne
        ops = []
        now = datetime.utcnow()
        for item in items:
            uri = item.get("uri")
            if not uri:
                continue
            item.setdefault("inserted_at", now)
            ops.append(UpdateOne(
                {"uri": uri},
                {"$setOnInsert": item},  # n'ecrit que si le doc n'existe pas encore
                upsert=True
            ))

        if not ops:
            return 0

        result = self.db.timeline.bulk_write(ops)
        return result.upserted_count  # nombre de NOUVEAUX documents inseres

