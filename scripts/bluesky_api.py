import time

import requests
import json

TIMELINE_API_URL = "https://bsky.social/xrpc/app.bsky.feed.getTimeline"
SEARCH_API_URL = "https://bsky.social/xrpc/app.bsky.feed.searchPosts"


def load_token():
    """Lit le token d'acces sauvegarde par 1_code_token.py."""
    with open("token.json", "r", encoding="utf-8") as f:
        return json.load(f)["accessJwt"]


def get_full_timeline(limit_per_call=100, max_pages=5):
    """Recupere le fil d'actualite de l'utilisateur connecte, page par page."""
    token = load_token()
    headers = {"Authorization": f"Bearer {token}"}

    all_items = []
    cursor = None

    for _ in range(max_pages):
        params = {"limit": limit_per_call}
        if cursor:
            params["cursor"] = cursor

        r = requests.get(TIMELINE_API_URL, headers=headers, params=params, timeout=10)
        r.raise_for_status()

        data = r.json()
        feed = data.get("feed", [])
        all_items.extend(feed)

        cursor = data.get("cursor")
        if not cursor:
            break

    return all_items


def search_posts(keyword, limit=100, cursor=None, retries=3):
    """Recherche une page de posts contenant un mot-cle, avec retry sur timeout/erreur reseau."""
    token = load_token()
    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": keyword, "limit": limit}
    if cursor:
        params["cursor"] = cursor

    for attempt in range(retries):
        try:
            r = requests.get(SEARCH_API_URL, headers=headers, params=params, timeout=30)
            if r.status_code != 200:
                print(f"  Erreur API {r.status_code} pour '{keyword}'")
                return None
            return r.json()
        except requests.exceptions.Timeout:
            wait = (attempt + 1) * 5
            print(f"  Timeout (tentative {attempt + 1}/{retries}), attente {wait}s...")
            time.sleep(wait)
        except requests.exceptions.ConnectionError:
            print(f"  Erreur reseau pour '{keyword}', tentative {attempt + 1}/{retries}")
            time.sleep(10)

    print(f"  Abandon apres {retries} tentatives pour '{keyword}'")
    return None


def bootstrap_from_keywords(mongo, keywords, pages_per_keyword=10, limit_per_page=100):
    """Importe dans Mongo les posts trouves pour chaque mot-cle (pagine jusqu'a epuisement)."""
    grand_total = 0

    for keyword in keywords:
        print(f"[{keyword}]")
        cursor = None  # pagination Bluesky : cursor=None -> premiere page
        keyword_total = 0

        for page in range(pages_per_keyword):
            data = search_posts(keyword, limit_per_page, cursor)

            if not data or "posts" not in data or not data["posts"]:
                print(f"  Fin a la page {page + 1}")
                break

            inserted = mongo.insert_timeline(data["posts"])
            nb = len(data["posts"])
            keyword_total += nb
            grand_total += nb
            print(f"  Page {page + 1} : {nb} recus, {inserted} nouveaux inseres")

            cursor = data.get("cursor")
            if not cursor:
                break

            time.sleep(0.5)  # evite de saturer le rate-limit de l'API Bluesky

        print(f"  Sous-total '{keyword}' : {keyword_total} posts\n")

    return grand_total
