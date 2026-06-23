# Étape 2 — Test de connexion à MongoDB Atlas
# Vérifie que la base de données est accessible avant de lancer
# les scripts d'ingestion (scripts 3 et 4).

import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError

# Lecture de l'URI MongoDB et du nom de la base depuis .env
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DBNAME = os.getenv("MONGO_DBNAME")


def test_connection():
    try:
        client = MongoClient(MONGO_URI)

        # La commande ping est le moyen officiel de valider la connexion Atlas
        client.admin.command("ping")
        print("Connexion MongoDB : OK")

        # Vérifie que la base cible (Bluesky) est bien accessible
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
