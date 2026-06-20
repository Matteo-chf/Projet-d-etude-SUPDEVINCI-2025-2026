# Étape 4 — Collecte massive de posts Bluesky par mots-clés (bootstrap)
# Contrairement au script 3 (timeline personnelle), ce script interroge
# l'endpoint de recherche (searchPosts) pour constituer un corpus varié
# couvrant des thèmes d'actualité : presse, politique, santé, environnement…
# Résultat attendu : plusieurs milliers de posts dans MongoDB.

import requests
import json
import time
from mongo_service import MongoService

# Endpoint de recherche de posts par mot-clé
API_URL = "https://bsky.social/xrpc/app.bsky.feed.searchPosts"

# Liste de mots-clés couvrant les domaines d'actualité pertinents
KEYWORDS = [
    # Noms de médias tels qu'écrits dans les posts Bluesky
    "reuters", "bbc news", "bloomberg", "afp", "apnews",
    "le monde", "le figaro", "libération", "france24", "francetvinfo",
    "rfi", "nouvel obs", "mediapart", "les echos", "bfmtv",
    "el pais", "der spiegel", "the guardian", "financial times",

    # Politique et société
    "election", "politics", "government", "democracy", "parliament",
    "politique", "élection", "gouvernement", "parlement", "sénat",

    # Santé publique
    "health", "vaccine", "covid", "who", "medicine",
    "santé", "vaccin", "épidémie", "oms", "médicament",

    # Environnement et climat
    "climate", "environment", "global warming", "renewable energy",
    "climat", "environnement", "réchauffement", "énergie renouvelable",

    # Économie et finance
    "economy", "inflation", "finance", "interest rates",
    "économie", "banque centrale", "croissance", "bourse",

    # Science et technologie
    "science", "research", "study", "artificial intelligence",
    "recherche", "découverte", "intelligence artificielle",

    # Géopolitique
    "ukraine", "war", "conflict", "migration", "nato",
    "guerre", "conflit", "otan", "diplomatie",

    # Justice et société
    "justice", "human rights", "corruption",
    "droits humains", "tribunal",
]

# Paramètres de pagination : 10 pages x 100 posts = 1 000 posts par mot-clé maximum
PAGES_PER_KEYWORD = 10
LIMIT_PER_PAGE = 100


def load_token():
    # Lit le token JWT généré par le script 1_code_token.py
    with open("token.json", "r", encoding="utf-8") as f:
        return json.load(f)["accessJwt"]


def get_posts(keyword, limit=100, cursor=None, retries=3):
    # Appel paginé à l'API de recherche Bluesky avec retry automatique sur timeout
    token = load_token()
    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": keyword, "limit": limit}
    if cursor:
        params["cursor"] = cursor

    for attempt in range(retries):
        try:
            r = requests.get(API_URL, headers=headers, params=params, timeout=30)
            if r.status_code != 200:
                print(f"  Erreur API {r.status_code} pour '{keyword}'")
                return None
            return r.json()
        except requests.exceptions.Timeout:
            # En cas de timeout, on attend et on réessaie
            wait = (attempt + 1) * 5
            print(f"  Timeout (tentative {attempt + 1}/{retries}), attente {wait}s...")
            time.sleep(wait)
        except requests.exceptions.ConnectionError:
            print(f"  Erreur réseau pour '{keyword}', tentative {attempt + 1}/{retries}")
            time.sleep(10)

    print(f"  Abandon après {retries} tentatives pour '{keyword}'")
    return None


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

            # Insertion dans MongoDB — les doublons sont ignorés (upsert sur uri)
            inserted = mongo.insert_timeline(data["posts"])
            nb = len(data["posts"])
            keyword_total += nb
            grand_total += nb
            print(f"  Page {page + 1} : {nb} recus, {inserted} nouveaux inseres")

            cursor = data.get("cursor")
            if not cursor:
                break

            # Pause pour respecter le rate-limit de l'API Bluesky
            time.sleep(0.5)

        print(f"  Sous-total '{keyword}' : {keyword_total} posts\n")

    print(f"Termine ! Total recu : ~{grand_total} posts (sans compter les doublons ignores)")
