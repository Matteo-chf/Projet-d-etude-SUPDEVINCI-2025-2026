# Étape 3 — Ingestion de la timeline Bluesky vers MongoDB
# Récupère les derniers posts du fil d'actualité de l'utilisateur authentifié
# (endpoint getTimeline) et les insère dans la collection MongoDB "timeline".
# Les doublons sont gérés automatiquement par MongoService (upsert sur l'uri).

from bluesky_api import get_full_timeline
from mongo_service import MongoService


def run():
    mongo = MongoService()

    # Récupère jusqu'à 5 pages de 100 posts chacune (500 posts max par exécution)
    timeline = get_full_timeline(limit_per_call=100, max_pages=5)

    inserted = mongo.insert_timeline(timeline)
    print(f"{inserted} documents inseres dans MongoDB")


if __name__ == "__main__":
    run()
