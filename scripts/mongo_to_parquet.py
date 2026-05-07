import os
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv

def run():
    print("🔄 Connexion à MongoDB...")
    load_dotenv("../.env")
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(uri)
    db = client["Bluesky"]
    collection = db["timeline"]
    
    # Extraire tous les documents
    print("📥 Extraction des données...")
    cursor = collection.find({})
    
    all_posts = []
    for doc in cursor:
        # Les posts bruts sont dans doc["data"]["posts"] pour "searchPosts"
        # OU "doc['data']['feed']" pour l'ancienne version
        if "data" in doc:
            data = doc["data"]
            if "posts" in data:
                for post in data["posts"]:
                    # On standardise au maximum. L'auteur et le texte sont dans "record" ou "post"
                    try:
                        record = post.get("record", {})
                        text = record.get("text", "")
                        created_at = record.get("createdAt", "")
                        if text:
                            all_posts.append({"text": text, "createdAt": created_at})
                    except Exception as e:
                        pass
            elif "feed" in data:
                for item in data["feed"]:
                    try:
                        post = item.get("post", {})
                        record = post.get("record", {})
                        text = record.get("text", "")
                        created_at = record.get("createdAt", "")
                        if text:
                            all_posts.append({"text": text, "createdAt": created_at})
                    except:
                        pass
                        
    print(f"✅ {len(all_posts)} posts textuels concaténés.")
    
    df = pd.DataFrame(all_posts)
    
    # Sécuriser les dossiers de destination
    os.makedirs("../pipeline-kedro/data/01_raw", exist_ok=True)
    parquet_path = "../pipeline-kedro/data/01_raw/bluesky_posts_raw.parquet"
    
    df.to_parquet(parquet_path)
    print(f"✅ Données enregistrées dans {parquet_path} pour traitement Kedro.")

if __name__ == "__main__":
    run()
