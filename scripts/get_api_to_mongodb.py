import requests
import json
from mongo_service import MongoService

# Point d'entrée de l'API Bluesky pour chercher les posts d'actualité (global)
API_URL = "https://bsky.social/xrpc/app.bsky.feed.searchPosts"


def load_token():
    """Charge le jeton d'authentification Bluesky depuis le fichier JSON"""
    with open("token.json", "r", encoding="utf-8") as f:
        return json.load(f)["accessJwt"]


def get_timeline(limit=100):
    """Requête l'API Bluesky pour rechercher des posts de news mondiales"""
    token = load_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    params = {"q": "news", "limit": limit}

    r = requests.get(API_URL, headers=headers, params=params, timeout=10)
    print("HTTP status:", r.status_code)
    r.raise_for_status() # Lève une exception si le statut n'est pas 200 OK
    return r.json()


if __name__ == "__main__":
    # Étape 1: Initialise la connexion à MongoDB
    mongo = MongoService()
    
    # Étape 2: Télécharge les 100 posts les plus récents (maximum par requête API souvent 100)
    data = get_timeline(100)
    
    # Étape 3: Insère la collection MongoDB
    inserted_id = mongo.insert_timeline(data)

    print("✅ Données insérées dans MongoDB :", inserted_id)
