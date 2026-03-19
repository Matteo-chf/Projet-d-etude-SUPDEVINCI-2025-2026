import requests
import json
import time
from urllib.parse import quote
from mongo_service import MongoService

API_URL = "https://bsky.social/xrpc/app.bsky.feed.searchPosts"

def load_token():
    with open("token.json", "r", encoding="utf-8") as f:
        return json.load(f)["accessJwt"]

def get_posts(limit=100, cursor=None):
    token = load_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Recherche mondiale avec un mot-clé générique qui renvoie beaucoup de posts
    params = {"q": "news", "limit": limit}
    if cursor:
        params["cursor"] = cursor

    r = requests.get(API_URL, headers=headers, params=params, timeout=10)
    
    if r.status_code != 200:
        print(f"Erreur API: {r.status_code}")
        return None
        
    return r.json()

if __name__ == "__main__":
    mongo = MongoService()
    print("🚀 Lancement du mode accéléré : Récupération de ~1 000 posts (Mondial)...")
    
    cursor = None
    total_posts = 0
    pages = 10 # 10 pages de 100 posts
    
    for i in range(pages):
        print(f"🔄 Récupération de la page {i+1}/{pages}...")
        data = get_posts(100, cursor)
        
        if not data or "posts" not in data or not data["posts"]:
            print("❌ Plus de données à récupérer ou erreur.")
            if data:
                print("Touches du JSON recu:", data.keys())
                print("JSON complet:", data)
            break
            
        inserted_id = mongo.insert_timeline(data)
        
        nb_posts = len(data["posts"])
        total_posts += nb_posts
        print(f"✅ {nb_posts} posts insérés (ID: {inserted_id})")
        
        cursor = data.get("cursor")
        if not cursor:
            break
            
        time.sleep(1)

    print(f"🎉 Terminé ! Un total de ~{total_posts} posts ont été ajoutés à MongoDB.")
