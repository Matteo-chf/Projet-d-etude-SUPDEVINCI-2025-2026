# Documentation technique — Fact-Checker IA

**Projet d'études M1 Data — SUP DE VINCI 2025-2026**
Plateforme de vérification de crédibilité d'informations par RAG (Retrieval-Augmented Generation),
combinant un corpus Bluesky labellisé, une recherche web temps réel sur sources fiables et le LLM Mistral AI.

> Les diagrammes d'architecture associés sont disponibles dans
> [`../architecture/`](../architecture/) (3 schémas Mermaid).

---

## 1. Présentation de la solution

Le Fact-Checker IA évalue la crédibilité d'une information saisie par l'utilisateur
et restitue un **score de 0 à 100**, un **verdict** (Fiable / À vérifier / Non fiable)
et une **justification** appuyée sur des sources citées.

Le système repose sur trois signaux complémentaires :

1. **RAG Bluesky** — recherche des posts les plus similaires dans un corpus de
   médias vérifiés, indexé par embeddings sémantiques.
2. **RAG Web** — recherche d'articles de presse récents (DuckDuckGo), filtrée sur
   une liste de domaines de confiance.
3. **Analyse sémantique locale** — un modèle entraîné (TF-IDF + émotions VADER +
   régression logistique) qui évalue le *style d'écriture* du texte.

Ces signaux sont synthétisés par **Mistral AI**, qui produit le score final et sa
justification.

---

## 2. Architecture de la solution

### 2.1 Vue par couches

| Couche | Composants | Rôle |
|---|---|---|
| **Sources** | API Bluesky (AT Protocol), DuckDuckGo, Wikipédia, API Mistral | Données brutes et services externes |
| **Ingestion** | Scripts `1` à `5b` | Authentification, collecte, labelisation, purge |
| **Préparation** | Pipelines Kedro `nlp_cleaning`, `vectorization` | Nettoyage du texte, vectorisation TF-IDF |
| **Apprentissage** | Pipeline Kedro `classification`, `10_build_rag_index.py` | Classifieur de fiabilité, index RAG MiniLM |
| **Stockage** | MongoDB, PostgreSQL, fichier `.npy` | Posts bruts/labellisés, résultats, index vectoriel |
| **Service** | `rag_service.py`, `web_search_service.py` | Orchestration RAG + appel Mistral |
| **Restitution** | Frontend Streamlit (`frontend/app.py`) | Interface de vérification |
| **Orchestration** | Airflow (DAG toutes les 30 min) | Automatisation de la chaîne batch |

### 2.2 Flux de données (résumé)

```
API Bluesky ─▶ MongoDB ─▶ Labelisation ─▶ Purge ─▶ Nettoyage NLP
                                                         │
                          ┌──────────────────────────────┘
                          ▼
              Vectorisation TF-IDF ─▶ Classification ─▶ PostgreSQL
                          │
                          ▼
              Index RAG MiniLM (.npy)
                          │
   Texte utilisateur ─▶ Service RAG ─(Bluesky + Web + sémantique)─▶ Mistral ─▶ Verdict
```

Le détail complet figure dans les diagrammes Mermaid du dossier `architecture/`.

---

## 3. Chaîne de traitement détaillée

### 3.1 Ingestion (scripts `1` à `4`)
- **`1_code_token.py`** — Authentification via `com.atproto.server.createSession`,
  sauvegarde des tokens JWT dans `token.json`.
- **`bluesky_api.py`** — Fonctions de collecte : `get_full_timeline` (fil de
  l'utilisateur) et `search_posts` / `bootstrap_from_keywords` (recherche par
  mots-clés, paginée, avec retry sur timeout).
- **`4_bootstrap_data.py`** — Constitue un corpus large à partir d'une liste de
  mots-clés d'actualité (presse internationale, politique, santé, climat…) et de
  domaines connus pour la désinformation.
- **`mongo_service.py`** — Insertion idempotente : `upsert` sur le champ `uri` via
  `$setOnInsert` (les doublons sont ignorés).

### 3.2 Labelisation (`5_label_sources.py`)
Deux signaux, par ordre de priorité :
1. **Handle vérifié** — un handle Bluesky personnalisé (ex. `reuters.com`) atteste
   d'une vérification DNS du domaine par Bluesky (équivalent du badge vérifié).
2. **Domaine du lien partagé** — à défaut de handle, le domaine de l'URL externe.

Le résultat (`reliable` / `unreliable` / `unknown`) est écrit dans le champ
`source_label`. Les listes `TRUSTED_DOMAINS` / `UNTRUSTED_DOMAINS` recensent
~150 domaines de presse, institutions, fact-checkers et sites de désinformation.

### 3.3 Purge (`5b_purge_unlabeled.py`)
Supprime de MongoDB tous les documents `unknown` ou non traités, pour ne conserver
que les données exploitables par l'entraînement (avec confirmation interactive).

### 3.4 Nettoyage NLP — pipeline Kedro `nlp_cleaning`
- `fetch_from_mongo` — extraction robuste du texte (gère 3 formats de documents :
  `searchPosts`, `timeline`, ancien format `data.feed`).
- `clean_posts` — minuscules, suppression des URLs / mentions / hashtags /
  ponctuation, normalisation des espaces. Sortie : `cleaned_bluesky_posts`.

### 3.5 Vectorisation — pipeline Kedro `vectorization`
`TfidfVectorizer` (max_features, n-grammes (1,2), `min_df`, `sublinear_tf`).
Produit la matrice `vectorized_posts` et l'artefact réutilisable
`tfidf_vectorizer.pickle`.

### 3.6 Classification — pipeline Kedro `classification`
- `add_emotion_features` — scores VADER (neg / neu / pos / compound).
- `train_classifier` — `LogisticRegression` (`class_weight="balanced"`) sur
  TF-IDF ⊕ émotions, split stratifié 80/20. Produit `reliability_score` et
  l'artefact `classifier_model.pickle`.
- `save_to_postgres` — persistance dans la table `classification_results` (upsert
  `ON CONFLICT`).

### 3.7 Index RAG (`10_build_rag_index.py`)
Encode les posts `reliable` avec **MiniLM**
(`paraphrase-multilingual-MiniLM-L12-v2`, 384 dims), normalise en L2 et sauvegarde
embeddings + métadonnées dans `pipeline-kedro/data/06_models/rag_index.npy`.

### 3.8 Service RAG (`rag_service.py`)
`RAGCredibilityService.score()` combine :
- `retrieve()` — top-K cosinus sur l'index Bluesky ;
- `search_web()` — articles de presse récents filtrés sur domaines fiables ;
- la classification sémantique locale transmise par le frontend ;
puis appelle **Mistral** (`mistral-small-latest`) avec un prompt structuré, et
parse la réponse JSON (`credibility_score`, `credibility_label`, `alignment`,
`justification`).

### 3.9 Frontend (`frontend/app.py`)
Interface Streamlit « presse » : saisie de la news, jauge de score, verdict
justifié, colonnes Posts Bluesky / Articles de presse, mots cliquables vers
Wikipédia (spaCy `fr_core_news_sm`), et historique des analyses.

---

## 4. Choix techniques et technologiques

| Besoin | Technologie | Justification |
|---|---|---|
| Collecte réseau social | **API Bluesky / AT Protocol** | API ouverte, gratuite, handles vérifiés par DNS = signal de fiabilité natif |
| Stockage documents | **MongoDB** | Schéma souple adapté aux posts hétérogènes ; upsert simple anti-doublon |
| Orchestration pipelines | **Kedro** | Pipelines modulaires, reproductibles, catalogue de données versionné |
| Ordonnancement | **Airflow** | DAG planifié (toutes les 30 min), dépendances explicites entre tâches |
| Vectorisation lexicale | **TF-IDF (scikit-learn)** | Léger, interprétable, suffisant pour une baseline de style |
| Analyse émotionnelle | **VADER** | Capture le registre alarmiste typique de la désinformation |
| Classification | **Régression logistique** | Baseline robuste, probabilités calibrables, `class_weight` pour le déséquilibre |
| Embeddings sémantiques | **MiniLM multilingue** | 384 dims, léger, multilingue (FR/EN), bon compromis qualité/vitesse |
| Recherche web | **DuckDuckGo (ddgs)** | Gratuit, sans clé API, résultats datés filtrables par domaine |
| Synthèse / scoring | **Mistral AI** | LLM performant disponible en tier gratuit (`mistral-small-latest`) |
| Résultats structurés | **PostgreSQL** | Requêtes analytiques sur les scores de classification |
| Interface | **Streamlit** | Prototype web rapide en Python pur |
| Conteneurisation | **Docker Compose** | Stack reproductible (Mongo, Postgres, Airflow, Kafka, Spark, Prometheus, Grafana) |

---

## 5. Installation et déploiement

### 5.1 Prérequis
- Python 3.10+
- Docker & Docker Compose (pour la stack d'infrastructure)
- Un compte Bluesky et une clé API Mistral

### 5.2 Variables d'environnement (`.env` à la racine)
```dotenv
BSKY_IDENTIFIER=...        # identifiant Bluesky
BSKY_PASSWORD=...          # mot de passe applicatif Bluesky
MONGO_URI=mongodb://localhost:27017
POSTGRES_URI=postgresql+psycopg2://airflow:airflow@localhost:5433/airflow
MISTRAL_API_KEY=...        # clé API Mistral
```

### 5.3 Dépendances Python
```bash
python -m venv venv
venv\Scripts\activate            # Windows (PowerShell : venv\Scripts\Activate.ps1)
pip install -r requirements.txt
python -m spacy download fr_core_news_sm
```

### 5.4 Infrastructure (Docker)
```bash
docker compose up -d              # MongoDB, PostgreSQL, Airflow, Kafka, Spark, Prometheus, Grafana
```
Services exposés : Airflow `:8080`, MongoDB `:27017`, PostgreSQL `:5433`,
Grafana `:3000`, Prometheus `:9090`.

### 5.5 Exécution de la chaîne (ordre)
```bash
python scripts/1_code_token.py            # 1. authentification
python scripts/4_bootstrap_data.py        # 2. collecte du corpus
python scripts/5_label_sources.py         # 3. labelisation
python scripts/5b_purge_unlabeled.py      # 4. purge des non-labellisés
python scripts/6_nlp_cleaning.py          # 5. nettoyage NLP   (Kedro)
python scripts/7_vectorization.py         # 6. vectorisation   (Kedro)
python scripts/8_classification.py        # 7. classification  (Kedro)
python scripts/10_build_rag_index.py      # 8. index RAG MiniLM
```

### 5.6 Déploiement automatisé (Airflow)
Le DAG `bluesky_pipeline` (`airflow/dags/bluesky_sync_dag.py`) enchaîne toutes les
30 minutes : `ingestion_mongo → nlp_cleaning → vectorization → classification → reporting`.

---

## 6. Modalités d'utilisation de la plateforme

### 6.1 Interface web (recommandée)
```bash
streamlit run frontend/app.py
```
1. Saisir ou coller le texte d'une news dans la zone de saisie.
2. Cliquer sur **Analyser ›**.
3. Lire le verdict : jauge de score, label, justification, posts Bluesky et
   articles de presse cités ; les noms propres sont cliquables vers Wikipédia.
4. L'historique des analyses est conservé dans la barre latérale (session).

### 6.2 Interface en ligne de commande
```bash
python scripts/11_rag_credibility.py "Texte de la news à vérifier."
python scripts/11_rag_credibility.py --top-k 8 "Texte…"   # plus de sources Bluesky
python scripts/11_rag_credibility.py --no-web "Texte…"     # sans recherche web
python scripts/11_rag_credibility.py                       # mode interactif
```

### 6.3 Interprétation du score
| Score | Label | Signification |
|---|---|---|
| 70 – 100 | ✅ **Fiable** | Information confirmée par les sources |
| 40 – 69 | ⚠️ **À vérifier** | Peu couverte ou ambiguë |
| 0 – 39 | ❌ **Non fiable** | Contredite par les sources |

---

## 7. Limites connues et perspectives
- **Rate-limit DuckDuckGo** — la recherche web peut être temporairement
  indisponible (retry automatique × 3, message d'erreur géré côté UI).
- **Couverture du corpus** — la pertinence du RAG Bluesky dépend de la taille et de
  la fraîcheur de la base labellisée.
- **Baseline de classification** — la régression logistique est volontairement
  simple ; un modèle plus riche (transformeur fine-tuné) est une piste d'évolution.
- **Dépendance LLM** — le score final repose sur Mistral ; une évaluation
  multi-LLM renforcerait la robustesse.
