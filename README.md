# 🕵️ Fake News Detector — SUPDEVINCI 2025/2026

Plateforme de détection de fake news sur **Bluesky**, combinant classification sémantique et RAG pour produire un score de crédibilité (0 → 100).

---

## 🧠 Comment ça fonctionne

**1. 🔤 Classification sémantique locale**
Le texte est vectorisé via **TF-IDF** (5000 features) et enrichi de scores émotionnels **VADER** (les fake news ont souvent un registre plus alarmiste). Une **Régression Logistique** prédit `fiable` ou `suspect` avec un seuil à 75 %.

**2. 📡 RAG Bluesky**
Un index de posts fiables vectorisés avec **MiniLM** (384 dimensions) permet de retrouver par similarité cosinus les publications les plus proches de la news analysée.

**3. 🌐 RAG Web**
Recherche temps réel via **DuckDuckGo** filtrée sur des domaines de confiance (Reuters, AFP, Le Monde…). Apporte le contexte factuel du moment.

**4. 🤖 Synthèse Mistral AI**
Mistral combine les trois sources et génère un score final + justification :

| Score | Label |
|---|---|
| 70 – 100 | ✅ Fiable |
| 40 – 69 | ⚠️ À vérifier |
| 0 – 39 | ❌ Non fiable |

---

## 🚀 Déploiement

### Prérequis
- 🐍 Python 3.10+
- 🐳 Docker Desktop
- 🔑 Comptes : [Bluesky](https://bsky.app) · [MongoDB Atlas](https://www.mongodb.com/atlas) · [Mistral AI](https://console.mistral.ai/)

### 1️⃣ Variables d'environnement

```bash
cp .env.example .env
```

Remplir `.env` :

```env
BSKY_IDENTIFIER=votre_handle.bsky.social
BSKY_PASSWORD=votre_mot_de_passe
MONGO_URI=mongodb+srv://user:password@cluster0.xxx.mongodb.net/
MONGO_DBNAME=Bluesky
MISTRAL_API_KEY=votre_cle_api_mistral
```

### 2️⃣ Installer les dépendances

```bash
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt
python -m spacy download fr_core_news_sm

cd pipeline-kedro && pip install -r requirements.txt && pip install -e . && cd ..
```

### 3️⃣ Lancer l'infrastructure Docker

```bash
docker-compose up -d
```

| Service | Accès |
|---|---|
| 🌀 Airflow | http://localhost:8080 — `admin / admin` |
| 🗄️ MongoDB | localhost:27017 |
| 🐘 PostgreSQL | localhost:5433 |
| 📊 Grafana | http://localhost:3000 |

### 4️⃣ Alimenter la base de données

```bash
python scripts/1_code_token.py          # Auth Bluesky
python scripts/4_bootstrap_data.py      # Collecte ~1100 posts
python scripts/5_label_sources.py       # Labelisation
python scripts/5b_purge_unlabeled.py    # Nettoyage
```

### 5️⃣ Entraîner le modèle

```bash
cd pipeline-kedro
kedro run --pipeline nlp_cleaning
kedro run --pipeline vectorization
kedro run --pipeline classification
cd ..
```

### 6️⃣ Construire l'index RAG

```bash
python scripts/10_build_rag_index.py
```

### 7️⃣ Lancer le fact-checker

```bash
streamlit run frontend/app.py
```

➡️ Ouvre **http://localhost:8501** — saisissez n'importe quelle actualité et obtenez son score de crédibilité instantanément.

---

> ⏰ **Automatisation** : le DAG Airflow relance automatiquement le pipeline toutes les 30 minutes une fois Docker démarré.
