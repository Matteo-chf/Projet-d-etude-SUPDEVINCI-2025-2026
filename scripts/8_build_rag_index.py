# Étape 8 — Construction de l'index RAG
# Lit les articles labelisés dans MongoDB, les vectorise avec MiniLM
# et sauvegarde l'index numpy pour une utilisation rapide lors des requêtes.
#
# Usage :  python scripts/8_build_rag_index.py
# Sortie : pipeline-kedro/data/06_models/rag_index.npy

import os    # chemins de fichiers
import re    # nettoyage du texte
import sys   # sortie du programme en cas d'erreur

import numpy as np                                      # sauvegarde et manipulation des matrices
from dotenv import find_dotenv, load_dotenv             # chargement du .env
from pymongo import MongoClient                         # connexion MongoDB
from sentence_transformers import SentenceTransformer   # modèle MiniLM (384 dims)
from sklearn.preprocessing import normalize             # normalisation L2 des vecteurs

load_dotenv(find_dotenv())

MODEL_NAME  = "paraphrase-multilingual-MiniLM-L12-v2"
BATCH_SIZE  = 64  # nombre d'articles encodés simultanément (ajuster selon la RAM)

BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PATH  = os.path.join(BASE_DIR, "pipeline-kedro", "data", "06_models", "rag_index.npy")


def clean_text(text: str) -> str:
    """Normalise le texte : minuscules, sans URLs / mentions / hashtags / ponctuation."""
    text = text.lower()
    text = re.sub(r"http\S+|www\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"#\w+", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_text(doc: dict) -> str:
    """Extrait le texte brut d'un document Bluesky (3 formats selon le script de collecte)."""
    # Format searchPosts (script 4) : post plat avec "record" et "author" à la racine
    if "record" in doc and "author" in doc:
        return doc["record"].get("text", "")

    # Format timeline (script 3) : post niché sous la clé "post"
    if "post" in doc:
        return doc["post"].get("record", {}).get("text", "")

    # Ancien format (script 3 initial) : plusieurs posts groupés dans data.feed
    if "data" in doc:
        for item in doc["data"].get("feed", []):
            text = item.get("post", {}).get("record", {}).get("text", "")
            if text:
                return text

    return ""


def fetch_labeled_docs() -> list[dict]:
    """Récupère depuis MongoDB tous les articles avec source_label reliable ou unreliable."""
    uri        = os.getenv("MONGO_URI")
    client     = MongoClient(uri)
    collection = client["Bluesky"]["timeline"]

    total = collection.count_documents({"source_label": "reliable"})
    print(f"Documents fiables trouvés : {total}")

    if total == 0:
        print("Aucun document fiable. Lancez d'abord : python scripts/5_label_sources.py")
        client.close()
        sys.exit(1)

    # Récupération : uniquement les sources fiables, champs nécessaires seulement
    docs = list(collection.find(
        {"source_label": "reliable"},
        {"_id": 0, "uri": 1, "source_label": 1, "record": 1, "author": 1, "post": 1, "data": 1}
    ))
    client.close()
    return docs


def build_index():
    print("\n=== Construction de l'index RAG ===\n")

    docs = fetch_labeled_docs()

    # Extraction du texte, nettoyage et construction de la liste de métadonnées
    metadata = []
    texts    = []
    skipped  = 0

    for doc in docs:
        raw     = extract_text(doc)
        cleaned = clean_text(raw)
        if len(cleaned) < 10:  # ignore les textes trop courts (sans contenu utile)
            skipped += 1
            continue
        texts.append(cleaned)
        metadata.append({
            "uri":          doc.get("uri", ""),
            "source_label": doc.get("source_label", "unknown"),
            "text":         cleaned,
        })

    print(f"Articles utilisables : {len(texts)} ({skipped} ignorés car texte trop court)\n")

    # Affichage de la répartition des labels
    label_counts = {}
    for m in metadata:
        lbl = m["source_label"]
        label_counts[lbl] = label_counts.get(lbl, 0) + 1
    for lbl, count in label_counts.items():
        print(f"  {lbl:12s} : {count}")

    # Chargement du modèle MiniLM (téléchargé automatiquement si absent)
    print(f"\nChargement du modèle MiniLM ({MODEL_NAME})…")
    encoder = SentenceTransformer(MODEL_NAME)

    # Encodage de tous les textes en vecteurs 384 dims
    print(f"Encodage de {len(texts)} articles (batch_size={BATCH_SIZE})…")
    embeddings = encoder.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
    )

    # Normalisation L2 faite une seule fois ici pour accélérer le cosinus à la requête
    embeddings_norm = normalize(embeddings)

    # Sauvegarde : dict numpy avec les embeddings + les métadonnées
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    np.save(OUTPUT_PATH, {"embeddings_norm": embeddings_norm, "metadata": metadata})

    print(f"\nIndex sauvegardé : {OUTPUT_PATH}")
    print(f"Shape embeddings  : {embeddings_norm.shape}")
    print("\nIndex RAG prêt. Lancez maintenant :")
    print("  python scripts/9_rag_credibility.py")


if __name__ == "__main__":
    build_index()
