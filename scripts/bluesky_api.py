# Client API Bluesky — endpoint getTimeline
# Récupère le fil d'actualité de l'utilisateur authentifié en paginant
# sur plusieurs appels successifs grâce au mécanisme de cursor AT Protocol.
# Utilisé par le script 3_job_bluesky_to_mongo.py.

import requests
import json

# Endpoint officiel AT Protocol pour la timeline personnelle
API_URL = "https://bsky.social/xrpc/app.bsky.feed.getTimeline"


def load_token():
    # Lit le token d'accès JWT généré par 1_code_token.py
    with open("token.json", "r", encoding="utf-8") as f:
        return json.load(f)["accessJwt"]


def get_full_timeline(limit_per_call=100, max_pages=5):
    """
    Récupère jusqu'à `max_pages` pages de `limit_per_call` posts chacune.
    Retourne une liste plate de tous les éléments du fil (feed items).
    """
    token = load_token()
    headers = {"Authorization": f"Bearer {token}"}

    all_items = []
    cursor = None

    for _ in range(max_pages):
        params = {"limit": limit_per_call}
        if cursor:
            # Le cursor est un opaque token fourni par l'API pour accéder à la page suivante
            params["cursor"] = cursor

        r = requests.get(API_URL, headers=headers, params=params, timeout=10)
        r.raise_for_status()

        data = r.json()
        feed = data.get("feed", [])
        all_items.extend(feed)

        cursor = data.get("cursor")
        # Absence de cursor = fin du fil disponible
        if not cursor:
            break

    return all_items
