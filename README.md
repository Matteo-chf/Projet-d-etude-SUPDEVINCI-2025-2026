# 🕵️ Fake News Detector — SUPDEVINCI 2025/2026

> Plateforme complète de détection de fake news sur **Bluesky** combinant un pipeline RAG (Retrieval-Augmented Generation), une classification sémantique TF-IDF + VADER, et une synthèse par **Mistral AI**.

---

## 📖 Présentation du projet

Ce projet de Master 2 (Traitement de flux d'information) implémente un **fact-checker intelligent** capable d'analyser n'importe quelle actualité et de lui attribuer un score de crédibilité de 0 à 100.

### 🧠 Comment ça marche ?

L'analyse repose sur **trois mécanismes complémentaires** :

#### 1. 🔤 Classification sémantique locale (TF-IDF + VADER)
- **TF-IDF** vectorise le texte en 5000 features (bigrammes, `min_df`, `sublinear_tf`)
- **VADER** ajoute 4 scores émotionnels (neg · neu · pos · compound) — les fake news ont souvent un registre plus alarmiste
- Une **Régression Logistique** (`class_weight=balanced`) combine les deux pour prédire `reliable` ou `unreliable`
- Seuil de décision relevé à **75 %** côté frontend (vs 50 % à l'entraînement) pour distinguer « fiable » d'un style simplement « suspect »

#### 2. 🔍 RAG Bluesky (base locale)
- Index MiniLM (`paraphrase-multilingual-L12`, 384 dims) construit sur les posts Bluesky labellisés fiables
- Similarité cosinus entre la requête et l'index → top-K articles les plus proches
- Chaque résultat est pondéré par son score de similarité

#### 3. 🌐 RAG Web (temps réel)
- Recherche live via **DuckDuckGo** (DDGS News + Text)
- Filtrée sur les domaines de confiance, triée du plus récent au plus ancien
- Apporte le contexte factuel du moment

#### 4. 🤖 Synthèse Mistral AI
Mistral reçoit les 4 sources priorisées (web > Bluesky > sémantique > similarité) et génère :

| Alignement | Score | Label |
|---|---|---|
| Confirmée | 70 – 100 | ✅ Fiable |
| Ambiguë / peu couverte | 40 – 69 | ⚠️ À vérifier |
| Contredite | 0 – 39 | ❌ Non fiable |

---

## 🏗️ Architecture globale

```
API Bluesky ──→ MongoDB ──→ Kedro (NLP cleaning) ──→ TF-IDF + VADER
                                                          │
                                              ┌───────────┴───────────┐
                                        PostgreSQL            Index MiniLM (RAG)
                                              │                       │
                                         Frontend Streamlit ←─────────┘
                                              │
                                    DuckDuckGo (web) + Mistral AI
```

**Stack technique :**
- 📥 **Ingestion** : API Bluesky (AT Protocol), scripts Python 1 → 5
- 🗄️ **Stockage** : MongoDB (posts bruts) + PostgreSQL (résultats de classification)
- ⚙️ **Orchestration** : Apache Airflow (DAG toutes les 30 min)
- 🔬 **ML Pipeline** : Kedro (nettoyage NLP, vectorisation, classification)
- 🖥️ **Frontend** : Streamlit
- 📡 **Big Data** : Kafka + Spark (infrastructure disponible via Docker)
- 📊 **Monitoring** : Prometheus + Grafana

---

## 📂 Structure du projet

```
.
├── scripts/                    # Pipeline d'ingestion et d'analyse (scripts 1 → 11)
│   ├── 1_code_token.py         # Authentification Bluesky → token.json
│   ├── 2_Mongodb_Connection.py # Test de connexion MongoDB
│   ├── 3_job_bluesky_to_mongo.py  # Collecte timeline → MongoDB
│   ├── 4_bootstrap_data.py     # Collecte massive (~1100 posts)
│   ├── 5_label_sources.py      # Labelisation reliable/unreliable
│   ├── 5b_purge_unlabeled.py   # Purge des posts sans label
│   ├── 6_nlp_cleaning.py       # Nettoyage NLP (minuscules, URL, ponctuation)
│   ├── 7_vectorization.py      # TF-IDF vectorisation
│   ├── 8_classification.py     # Entraînement Logistic Regression
│   ├── 9_reporting.py          # Rapport de performance
│   ├── 10_build_rag_index.py   # Construction de l'index MiniLM
│   ├── 11_rag_credibility.py   # Score RAG via Mistral
│   ├── rag_service.py          # Service RAG (Bluesky + Web + Mistral)
│   └── web_search_service.py   # Recherche DuckDuckGo
├── pipeline-kedro/             # Pipeline Kedro (nettoyage + vectorisation + classification)
├── frontend/
│   └── app.py                  # Interface Streamlit (fact-checker)
├── airflow/dags/               # DAG Airflow (orchestration automatique)
├── monitoring/                 # Config Prometheus
├── docs/                       # Cahier des charges & documentation
├── structure/architecture/     # Diagrammes Mermaid de l'architecture
├── docker-compose.yml          # Tous les services (Airflow, Kafka, Spark, MongoDB…)
├── requirements.txt            # Dépendances Python (scripts + frontend)
└── .env.example                # Variables d'environnement à copier
```

---

## 🚀 Installation & Lancement

### Prérequis

- 🐍 **Python 3.10+**
- 🐳 **Docker Desktop** (pour Airflow, MongoDB, Kafka, Spark…)
- 🔑 **Comptes requis** : Bluesky + MongoDB Atlas (ou local) + [Mistral AI](https://console.mistral.ai/)

---

### ⚙️ Étape 1 — Cloner le projet

```bash
git clone https://github.com/votre-org/Projet-d-etude-SUPDEVINCI-2025-2026.git
cd Projet-d-etude-SUPDEVINCI-2025-2026
```

---

### 🔐 Étape 2 — Configurer les variables d'environnement

```bash
cp .env.example .env
```

Editer `.env` avec vos identifiants :

```env
BSKY_IDENTIFIER=votre_handle.bsky.social
BSKY_PASSWORD=votre_mot_de_passe

MONGO_URI=mongodb+srv://user:password@cluster0.xxx.mongodb.net/
MONGO_DBNAME=Bluesky

MISTRAL_API_KEY=votre_cle_api_mistral
```

---

### 📦 Étape 3 — Installer les dépendances Python

```bash
# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# Dépendances principales (scripts + frontend)
pip install -r requirements.txt

# Modèle spaCy pour l'extraction de mots-clés (français)
python -m spacy download fr_core_news_sm

# Dépendances du pipeline Kedro
cd pipeline-kedro
pip install -r requirements.txt
pip install -e .
cd ..
```

---

### 🐳 Étape 4 — Lancer l'infrastructure Docker

```bash
docker-compose up -d
```

Services démarrés :

| Service | URL / Port |
|---|---|
| 🌀 Airflow UI | http://localhost:8080 (admin / admin) |
| 🗄️ MongoDB | localhost:27017 |
| 🐘 PostgreSQL | localhost:5433 |
| ⚡ Kafka | localhost:9092 |
| 🔥 Spark Master | localhost:8081 |
| 📊 Grafana | http://localhost:3000 |
| 📡 Prometheus | http://localhost:9090 |

---

### 🔄 Étape 5 — Alimenter la base de données

```bash
# 1. Authentification Bluesky
python scripts/1_code_token.py

# 2. Collecte massive de posts (bootstrap ~1100 posts)
python scripts/4_bootstrap_data.py

# 3. Labelisation des sources
python scripts/5_label_sources.py

# 4. Purge des posts sans label
python scripts/5b_purge_unlabeled.py
```

---

### 🤖 Étape 6 — Entraîner le modèle de classification

```bash
# Via Kedro (pipeline complet)
cd pipeline-kedro
kedro run --pipeline nlp_cleaning
kedro run --pipeline vectorization
kedro run --pipeline classification

# Ou manuellement
cd ..
python scripts/6_nlp_cleaning.py
python scripts/7_vectorization.py
python scripts/8_classification.py
```

---

### 📡 Étape 7 — Construire l'index RAG

```bash
python scripts/10_build_rag_index.py
```

Génère `rag_index.npy` — index MiniLM des posts fiables (384 dimensions, similarité cosinus).

---

### 🖥️ Étape 8 — Lancer le frontend

```bash
streamlit run frontend/app.py
```

Ouvre automatiquement **http://localhost:8501**

➡️ Saisissez n'importe quelle actualité et obtenez instantanément :
- 🎯 Un score de crédibilité (0 → 100)
- ⚖️ Un verdict IA (✅ Fiable / ⚠️ À vérifier / ❌ Non fiable)
- 📰 Les articles de presse sources (DuckDuckGo)
- 🦋 Les posts Bluesky similaires
- 🔗 Des mots-clés cliquables vers Wikipédia

---

### ⏰ Automatisation (optionnel)

L'orchestration via Airflow s'exécute toutes les **30 minutes** automatiquement (après `docker-compose up`). Elle chaîne :
1. Collecte des nouveaux posts Bluesky
2. Labelisation + nettoyage NLP
3. Ré-entraînement du vecteur TF-IDF

---

## 🧪 Tester le système

```bash
# Tester une news en ligne de commande
python scripts/test_single_news.py

# Tester le pipeline RAG complet
python scripts/11_rag_credibility.py

# Rapport de performance du modèle
python scripts/9_reporting.py
```

---

## 👥 Équipe

Projet réalisé dans le cadre du **Master 2 Data Engineering — SUPDEVINCI 2025/2026**

---

## 📄 Licence

Usage académique — SUPDEVINCI 2025/2026
