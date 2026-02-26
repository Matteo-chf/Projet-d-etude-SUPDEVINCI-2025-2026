import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError

# Charger les variables du fichier .env
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DBNAME = os.getenv("MONGO_DBNAME")

def test_connection():
    try:
        client = MongoClient(MONGO_URI)
    
        client.admin.command("ping")
        print("Connexion MongoDB : OK")

        db = client[MONGO_DBNAME]
        print(f"Base accessible : {MONGO_DBNAME}")

    except ConnectionFailure:
        print(" Échec de connexion : serveur MongoDB inaccessible.")
    except PyMongoError as e:
        print(f" Erreur PyMongo : {e}")
    except Exception as e:
        print(f" Erreur inattendue : {e}")

if __name__ == "__main__":
    test_connection()