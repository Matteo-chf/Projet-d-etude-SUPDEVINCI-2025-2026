import requests
import json
from mongo_service import MongoService

API_URL = "https://bsky.social/xrpc/app.bsky.feed.getTimeline"


def load_token():
    with open("token.json", "r", encoding="utf-8") as f:
        return json.load(f)["accessJwt"]


def get_timeline(limit=1000):
    token = load_token()
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get(f"{API_URL}?limit={limit}", headers=headers, timeout=10)
    print("HTTP status:", r.status_code)
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    mongo = MongoService()          # 🔹 Connexion Mongo
    data = get_timeline(10)         # 🔹 Appel API
    inserted_id = mongo.insert_timeline(data)  # 🔹 INSERTION

    print("✅ Données insérées dans MongoDB :", inserted_id)
