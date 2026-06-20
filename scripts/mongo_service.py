# Service MongoDB — couche d'accès à la base Bluesky
# Encapsule la connexion et les opérations d'écriture sur la collection "timeline".
# Utilise des upserts (UpdateOne avec upsert=True) pour éviter les doublons :
# si un document avec le même "uri" existe déjà, il est ignoré ($setOnInsert).

from pymongo import MongoClient, UpdateOne
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()


class MongoService:
    def __init__(self):
        # Connexion à MongoDB Atlas via l'URI défini dans .env
        uri = os.getenv("MONGO_URI")
        self.client = MongoClient(uri)
        self.db = self.client["Bluesky"]

    def insert_timeline(self, items):
        """
        Insère une liste de posts Bluesky dans la collection "timeline".
        Chaque document est identifié par son champ "uri" (clé unique AT Protocol).
        Retourne le nombre de nouveaux documents réellement insérés.
        """
        if not items:
            return 0

        ops = []
        now = datetime.utcnow()

        for item in items:
            uri = item.get("uri")
            if not uri:
                # Ignore les documents sans identifiant uri
                continue
            # Horodatage d'insertion pour traçabilité
            item.setdefault("inserted_at", now)
            ops.append(UpdateOne(
                {"uri": uri},
                # $setOnInsert : n'écrit les données que lors d'une vraie insertion (pas de mise à jour)
                {"$setOnInsert": item},
                upsert=True
            ))

        if not ops:
            return 0

        result = self.db.timeline.bulk_write(ops)
        return result.upserted_count
