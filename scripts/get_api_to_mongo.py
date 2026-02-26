import requests
import json
import os
from mongo_service import MongoService

API_URL = "https://bsky.social/xrpc/app.bsky.feed.getTimeline"

print(os.getcwd())  # 🔹 Affiche le répertoire de travail actuel pour debug

def load_token():
    with open("token.json", "r", encoding="utf-8") as f:
        return json.load(f)["accessJwt"]

def get_timeline(limit=10):
    token = load_token()
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get(f"{API_URL}?limit={limit}", headers=headers, timeout=10)
    print("HTTP status:", r.status_code)
    r.raise_for_status()
    return r.json()

if __name__ == "__main__":
    mongo = MongoService()
    data = get_timeline(5)

    mongo.insert_timeline(data)
