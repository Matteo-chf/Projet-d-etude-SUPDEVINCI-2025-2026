import re
import pickle
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from pathlib import Path
import glob

# Charge le vectorizer et le classifieur entraînes (versions les plus recentes)
project_root = Path(__file__).parent.parent

# Cherche les fichiers versionnés (Kedro crée un sous-dossier avec timestamp)
vectorizer_files = sorted(glob.glob(str(project_root / "pipeline-kedro" / "data" / "06_models" / "tfidf_vectorizer.pickle" / "*" / "*.pickle")))
classifier_files = sorted(glob.glob(str(project_root / "pipeline-kedro" / "data" / "06_models" / "classifier_model.pickle" / "*" / "*.pickle")))

if not vectorizer_files or not classifier_files:
    print("Erreur : fichiers du modele non trouves. Relance le pipeline classification d'abord.")
    exit(1)

vectorizer_path = Path(vectorizer_files[-1])  # Le plus recent
classifier_path = Path(classifier_files[-1])  # Le plus recent

with open(vectorizer_path, "rb") as f:
    vectorizer = pickle.load(f)

with open(classifier_path, "rb") as f:
    classifier = pickle.load(f)

analyzer = SentimentIntensityAnalyzer()


def clean_text(text: str) -> str:
    # Meme logique que nlp_cleaning.py
    text = text.lower()
    text = re.sub(r"http\S+|www\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"#\w+", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def predict_news(text: str):
    # Nettoyage
    cleaned = clean_text(text)
    if not cleaned:
        return {"error": "Texte vide apres nettoyage"}

    # Features emotion (VADER)
    scores = analyzer.polarity_scores(cleaned)
    emotion_features = {
        "emotion_neg": scores["neg"],
        "emotion_neu": scores["neu"],
        "emotion_pos": scores["pos"],
        "emotion_compound": scores["compound"],
    }

    # Vectorisation TF-IDF
    tfidf_vec = vectorizer.transform([cleaned]).toarray()[0]

    # Construction du vecteur complet (TF-IDF + emotion)
    feature_vector = list(tfidf_vec) + list(emotion_features.values())

    # Prediction
    pred_proba = classifier.predict_proba([feature_vector])[0]
    pred_label = classifier.predict([feature_vector])[0]

    return {
        "texte_original": text[:100] + "..." if len(text) > 100 else text,
        "texte_nettoye": cleaned[:100] + "..." if len(cleaned) > 100 else cleaned,
        "emotion_compound": emotion_features["emotion_compound"],
        "reliability_score": round(pred_proba[1], 4),  # proba reliable
        "predicted_label": "reliable" if pred_label == 1 else "unreliable",
        "confidence": round(max(pred_proba) * 100, 2),
    }


if __name__ == "__main__":
    print("=" * 70)
    print("TEST DU CLASSIFIEUR : DETECTABLE DE FIABILITE DE NEWS")
    print("=" * 70)

    test_texts = [
        "Reuters reports that the government announces new climate policies to reduce carbon emissions by 50% by 2030.",
        "SHOCKING: Scientists discover aliens have been controlling world governments! This is the biggest coverup in history!",
        "BBC News: Latest election results show record voter turnout across the country.",
    ]

    for i, text in enumerate(test_texts, 1):
        print(f"\n--- News #{i} ---")
        result = predict_news(text)
        if "error" not in result:
            print(f"Texte: {result['texte_original']}")
            print(f"Score fiabilite: {result['reliability_score']} (0=fake, 1=fiable)")
            print(f"Label: {result['predicted_label'].upper()}")
            print(f"Confiance: {result['confidence']}%")
            print(f"Emotion (compound): {result['emotion_compound']:.3f}")
        else:
            print(f"Erreur: {result['error']}")

    print("\n" + "=" * 70)
    print("Entrez votre propre news pour tester:")
    print("=" * 70)
    while True:
        text = input("\nNews (ou 'quit' pour quitter): ").strip()
        if text.lower() == "quit":
            break
        result = predict_news(text)
        if "error" not in result:
            print(f"Score fiabilite: {result['reliability_score']} (0=fake, 1=fiable)")
            print(f"Label: {result['predicted_label'].upper()}")
            print(f"Confiance: {result['confidence']}%")
        else:
            print(f"Erreur: {result['error']}")
