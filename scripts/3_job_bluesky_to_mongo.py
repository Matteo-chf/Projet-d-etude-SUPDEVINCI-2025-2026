from bluesky_api import get_full_timeline
from mongo_service import MongoService

def run():
    mongo = MongoService()
    timeline = get_full_timeline(limit_per_call=100, max_pages=5)
    inserted = mongo.insert_timeline(timeline)
    print(f"{inserted} documents inseres dans MongoDB")

if __name__ == "__main__":
    run()

