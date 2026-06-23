import re
import pickle
import glob
from pathlib import Path
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

project_root = Path(__file__).parent.parent
v_files = sorted(glob.glob(str(project_root / "pipeline-kedro" / "data" / "06_models" / "tfidf_vectorizer.pickle" / "*" / "*.pickle")))
c_files = sorted(glob.glob(str(project_root / "pipeline-kedro" / "data" / "06_models" / "classifier_model.pickle" / "*" / "*.pickle")))

vectorizer = pickle.load(open(v_files[-1], "rb"))
classifier = pickle.load(open(c_files[-1], "rb"))
analyzer = SentimentIntensityAnalyzer()

# <-- Modifie le texte ici pour tester ta propre news -->
news = "Breaking news: Scientists confirm climate change is real and urgent action is needed"

cleaned = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", re.sub(r"@\w+|#\w+|http\S+", "", news.lower()))).strip()
scores = analyzer.polarity_scores(cleaned)
tfidf = vectorizer.transform([cleaned]).toarray()[0]
features = list(tfidf) + [scores["neg"], scores["neu"], scores["pos"], scores["compound"]]
proba = classifier.predict_proba([features])[0]

print(f"Texte    : {news[:70]}...")
print(f"Score    : {proba[1]:.4f} (0=fake, 1=fiable)")
print(f"Label    : {'RELIABLE' if proba[1] > 0.5 else 'UNRELIABLE'}")
print(f"Confiance: {max(proba)*100:.1f}%")
