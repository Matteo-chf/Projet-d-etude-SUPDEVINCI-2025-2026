import requests
import json
import time
from mongo_service import MongoService

API_URL = "https://bsky.social/xrpc/app.bsky.feed.searchPosts"

KEYWORDS = [
    # Presse et actualité générale
    "news", "breaking news", "reuters", "bbc news", "apnews",
    # Politique et société
    "election", "politics", "government", "democracy", "parliament",
    # Santé
    "health", "vaccine", "covid", "who", "medicine",
    # Environnement
    "climate", "environment", "global warming",
    # Économie
    "economy", "inflation", "finance",
    # Géopolitique
    "ukraine", "war", "conflict", "migration",
]

PAGES_PER_KEYWORD = 10
LIMIT_PER_PAGE = 100


def load_token():
    with open("token.json", "r", encoding="utf-8") as f:
        return json.load(f)["accessJwt"]


def get_posts(keyword, limit=100, cursor=None):
    token = load_token()
    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": keyword, "limit": limit}
    if cursor:
        params["cursor"] = cursor

    r = requests.get(API_URL, headers=headers, params=params, timeout=10)
    if r.status_code != 200:
        print(f"  Erreur API {r.status_code} pour '{keyword}'")
        return None
    return r.json()


if __name__ == "__main__":
    mongo = MongoService()
    grand_total = 0

    estimated = len(KEYWORDS) * PAGES_PER_KEYWORD * LIMIT_PER_PAGE
    print(f"Lancement : {len(KEYWORDS)} mots-cles x {PAGES_PER_KEYWORD} pages x {LIMIT_PER_PAGE} posts = ~{estimated} posts max")
    print(f"(les doublons sont ignores automatiquement)\n")

    for keyword in KEYWORDS:
        print(f"[{keyword}]")
        cursor = None
        keyword_total = 0

        for page in range(PAGES_PER_KEYWORD):
            data = get_posts(keyword, LIMIT_PER_PAGE, cursor)

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

            time.sleep(0.5)

        print(f"  Sous-total '{keyword}' : {keyword_total} posts\n")

    print(f"Termine ! Total recu : ~{grand_total} posts (sans compter les doublons ignores)")
