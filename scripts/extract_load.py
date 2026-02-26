import requests
from pymongo import MongoClient

def run():
    response = requests.get("https://api.exemple.com/data")
    response.raise_for_status()
    data = response.json()

    client = MongoClient("mongodb://mongo:27017/")
    db = client["my_database"]
    collection = db["my_collection"]

    collection.insert_many(data)
    print("✅ Données insérées dans MongoDB")

if __name__ == "__main__":
    run()
