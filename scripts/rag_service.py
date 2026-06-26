# Service RAG — Crédibilité des informations (corpus fiable + recherche web)
#
# Flux combiné :
#   1. RAG MongoDB  : top-K articles similaires depuis la base Bluesky labelisée
#   2. RAG Web      : recherche DuckDuckGo filtrée sur domaines fiables (temps réel)
#   3. Mistral      : reçoit les deux contextes → score + justification
#
# Score : confirmé par sources → fiable | contredit → non fiable | non couvert → à vérifier

import json       # parse la réponse JSON de Mistral
import os         # lecture des variables d'environnement
import re         # nettoyage du texte et extraction JSON

from mistralai.client import Mistral                    # client officiel pour l'API Mistral (v2+)
from web_search_service import search_web                # recherche DuckDuckGo sur sources fiables
import numpy as np                                      # matrices d'embeddings
from dotenv import find_dotenv, load_dotenv             # chargement du .env
from sentence_transformers import SentenceTransformer   # modèle MiniLM (embeddings 384 dims)
from sklearn.metrics.pairwise import cosine_similarity  # mesure de similarité entre vecteurs
from sklearn.preprocessing import normalize             # normalisation L2 des vecteurs

load_dotenv(find_dotenv())

MODEL_NAME    = "paraphrase-multilingual-MiniLM-L12-v2"  # multilingue, léger, 384 dims
MISTRAL_MODEL = "mistral-small-latest"                    # disponible sur le tier gratuit

DEFAULT_INDEX_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "pipeline-kedro", "data", "06_models", "rag_index.npy"
)

LABEL_FR   = {"reliable": "FIABLE", "unreliable": "NON FIABLE", "suspect": "À VÉRIFIER"}
LABEL_ICON = {"reliable": "✅", "unreliable": "❌", "suspect": "⚠️"}

# Seuil de similarité en dessous duquel aucune source n'est vraiment pertinente
SIMILARITY_THRESHOLD = 0.25


def clean_text(text: str) -> str:
    """Normalise le texte : minuscules, sans URLs / mentions / hashtags / ponctuation."""
    text = text.lower()
    text = re.sub(r"http\S+|www\S+", "", text)  # supprime les URLs
    text = re.sub(r"@\w+", "", text)            # supprime les mentions
    text = re.sub(r"#\w+", "", text)            # supprime les hashtags
    text = re.sub(r"[^\w\s]", " ", text)        # remplace la ponctuation par des espaces
    return re.sub(r"\s+", " ", text).strip()


class RAGCredibilityService:
    def __init__(self, index_path: str = DEFAULT_INDEX_PATH):
        # Chargement du modèle d'embedding (téléchargé automatiquement la première fois)
        print("Chargement du modèle MiniLM…")
        self.encoder = SentenceTransformer(MODEL_NAME)

        if not os.path.exists(index_path):
            raise FileNotFoundError(
                f"Index RAG introuvable : {index_path}\n"
                "Construisez-le d'abord avec :\n"
                "  python scripts/10_build_rag_index.py"
            )

        # Chargement de l'index numpy : embeddings pré-normalisés + métadonnées
        print(f"Chargement de l'index RAG : {index_path}")
        data = np.load(index_path, allow_pickle=True).item()
        self.embeddings_norm = data["embeddings_norm"]  # shape (N, 384), normalisé L2
        self.metadata        = data["metadata"]         # list[dict] : uri, text

        # Client Mistral (utilise MISTRAL_API_KEY depuis .env)
        self.client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
        print(f"Index chargé : {len(self.metadata)} articles fiables indexés.\n")

    def retrieve(self, text: str, top_k: int = 5) -> list[dict]:
        """Retourne les top_k articles fiables les plus similaires avec leur score cosinus."""
        cleaned  = clean_text(text)
        emb      = self.encoder.encode([cleaned], convert_to_numpy=True)
        emb_norm = normalize(emb)  # normalisation L2 pour que le produit scalaire = cosinus

        # Calcul des similarités entre la requête et tous les articles indexés
        sims    = cosine_similarity(emb_norm, self.embeddings_norm)[0]
        top_idx = np.argsort(sims)[::-1][:top_k]  # indices des top_k plus similaires

        return [
            {**self.metadata[i], "similarity": float(sims[i])}
            for i in top_idx
        ]

    def score(
        self,
        text: str,
        top_k: int = 5,
        use_web: bool = True,
        classification: dict | None = None,
    ) -> dict:
        """
        Évalue la crédibilité via RAG MongoDB + RAG Web + Mistral.
        `classification` (optionnel) est le résultat de l'analyse sémantique
        locale (classify_local côté frontend) : transmis à Mistral comme
        indice complémentaire sur le style d'écriture du texte.
        Retourne : credibility_score, credibility_label, alignment,
                   justification, sources_used (MongoDB), web_articles.
        """
        # --- RAG MongoDB : articles similaires depuis la base Bluesky ---
        retrieved = self.retrieve(text, top_k)
        avg_sim   = float(np.mean([r["similarity"] for r in retrieved]))

        mongo_blocks = []
        for i, r in enumerate(retrieved, 1):
            sim_pct = f"{r['similarity']:.0%}"
            snippet = r.get("text", "")[:300].strip()
            mongo_blocks.append(f"Source base {i} (similarité={sim_pct}) :\n{snippet}")
        mongo_context = "\n\n".join(mongo_blocks)

        # --- RAG Web : recherche DuckDuckGo sur domaines fiables (triés du plus récent au plus ancien) ---
        web_articles = []
        web_context  = ""
        web_error    = None
        if use_web:
            print("  Recherche web en cours…")
            web_articles, web_error = search_web(text, max_results=10)
            if web_articles:
                web_blocks = []
                for i, a in enumerate(web_articles, 1):
                    snippet = a.get("snippet", "")[:300].strip()
                    domain  = a.get("source_domain", "")
                    title   = a.get("title", "")
                    date    = a.get("date", "")
                    date_tag = f" ({date[:10]})" if date else ""
                    web_blocks.append(f"Article web {i} [{domain}]{date_tag} — {title} :\n{snippet}")
                web_context = "\n\n".join(web_blocks)

        # Indique à Mistral si le sujet est couvert dans la base locale
        coverage_note = (
            f"Similarité moyenne base locale : {avg_sim:.0%}. "
            + ("Sujet bien représenté dans la base."
               if avg_sim >= SIMILARITY_THRESHOLD
               else "Sujet PEU représenté dans la base locale.")
        )

        # Prompt combiné : contexte MongoDB + contexte web
        web_section = f"""
=== ARTICLES WEB TROUVÉS (sources fiables, du plus récent au plus ancien) ===
{web_context if web_context else "Aucun article web trouvé pour cette requête."}
""" if use_web else ""

        # Signal complémentaire : analyse sémantique locale (style d'écriture)
        semantic_section = ""
        semantic_impact = ""
        if classification:
            sem_pct   = round(classification["score"] * 100)
            sem_conf  = round(classification.get("confidence", 0) * 100)
            sem_label = "fiable" if classification["label"] == "reliable" else "suspect"
            semantic_section = f"""
=== ANALYSE SÉMANTIQUE LOCALE (TF-IDF + émotions, indice important) ===
Un modèle local (TF-IDF + analyse émotionnelle VADER) évalue à {sem_pct}% la probabilité que le
style d'écriture du texte (vocabulaire, ton, charge émotionnelle) corresponde à celui de sources fiables.
Confiance du modèle : {sem_conf}%. Verdict stylométrique : {sem_label.upper()}.

⚠️ ATTENTION : Une analyse sémantique suspe (style d'écriture problématique) doit peser significativement
sur le score final, surtout en cas de couverture faible dans les sources factuelles. Elle signale un risque
réel (style manipulateur, polarisé, sensationnaliste).
"""
            semantic_impact = (
                "\n- Si l'analyse sémantique juge le texte SUSPECT (score < 75%), "
                "cela doit baisser significativement le score (jusqu'à -20 points), "
                "même si les sources factuelles sont ambiguës."
                "\n- Si l'analyse sémantique juge le texte FIABLE (score >= 75%), "
                "cela peut augmenter modérément le score en cas d'ambiguïté factuelle."
            )

        prompt = f"""Tu es un expert en fact-checking. Évalue si l'information est confirmée, contredite ou non couverte, à partir de quatre sources par ordre de priorité :
1. Articles web (presse) récents et fiables — PRIORITAIRES
2. Posts Bluesky de médias vérifiés (Reuters, BBC, AFP, Le Monde…) — complémentaires
3. Analyse sémantique locale (style d'écriture, vocabulaire, charge émotionnelle) — IMPORTANTE
4. Similarité avec sources fiables existantes — contexte général

=== INFORMATION À ANALYSER ===
{text}

=== SOURCES BASE LOCALE (posts Bluesky fiables) ===
{mongo_context}
{web_section}{semantic_section}
=== CONTEXTE ===
{coverage_note}

=== RÈGLES DE SCORING ===
- Confirmée par les sources → score 70-100. Contredite → 0-39. Peu couverte ou ambiguë → 40-69.
- Pondération : articles web > posts Bluesky > analyse sémantique > similarité générale.
  Les articles web les plus récents pèsent davantage que les plus anciens.
- En cas de désaccord, privilégie les articles web. Les posts Bluesky et l'analyse sémantique
  restent des indices complémentaires importants à toujours prendre en compte.{semantic_impact}
- L'analyse sémantique est un indice IMPORTANT : elle signale des risques de manipulation
  (ton sensationnaliste, polarisé, vocabulaire émotionnel excessif). Un texte au style
  suspect doit réduire le score, surtout si les sources factuelles sont peu couverte ou ambigues.

Réponds UNIQUEMENT en JSON valide avec exactement ces champs :
{{
  "credibility_score": <entier 0-100>,
  "credibility_label": <"reliable" si score>=70, "suspect" si 40<=score<70, "unreliable" si score<40>,
  "alignment": <"confirmed" | "contradicted" | "not_covered">,
  "justification": "<2-3 phrases expliquant le score en citant les sources>"
}}"""

        # Appel à l'API Mistral
        response = self.client.chat.complete(
            model=MISTRAL_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.choices[0].message.content.strip()

        # Extraction du JSON (Mistral peut ajouter du texte autour)
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not json_match:
            return {"error": "Réponse Mistral non parseable", "raw": raw}

        result = json.loads(json_match.group())
        result["avg_similarity"] = round(avg_sim, 3)
        result["sources_used"]   = retrieved    # sources MongoDB
        result["web_articles"]   = web_articles # articles web trouvés (du plus récent au plus ancien)
        result["web_error"]      = web_error    # None si OK, message si échec
        return result
