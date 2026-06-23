# Architecture du projet — Bluesky News Credibility

## 1. Vue d'ensemble du projet

```mermaid
graph TD
    subgraph Sources
        API[Bluesky API]
    end

    subgraph Ingestion ["Scripts d'ingestion (scripts/)"]
        S1[1_code_token.py\nAuthentification JWT]
        S2[3_job_bluesky_to_mongo.py\nTimeline personnelle]
        S3[4_bootstrap_data.py\nRecherche par mots-clés]
        S4[5_label_sources.py\nLabellisation domaines]
    end

    subgraph Storage ["Stockage"]
        MDB[(MongoDB Atlas\nBluesky.timeline)]
        PG[(PostgreSQL\nclassification_results)]
        IDX[(rag_index.npy\nembeddings MiniLM)]
    end

    subgraph Orchestration
        AF[Apache Airflow\nDAG toutes les 30 min]
    end

    subgraph ML ["Pipeline ML batch — Kedro"]
        P1[nlp_cleaning\nNettoyage texte]
        PV[vectorization\nTF-IDF]
        PC[classification\nVADER + Logistic Regression]
    end

    subgraph RAG ["RAG interactif — scripts 10/11 + frontend"]
        R1[10_build_rag_index.py\nIndex MiniLM des sources fiables]
        R2[11_rag_credibility.py / frontend\nRAG Mongo + Web + Mistral]
    end

    API --> S2
    API --> S3
    S1 --> S2
    S2 --> MDB
    S3 --> MDB
    S4 --> MDB

    AF -->|orchestre| S2
    AF -->|orchestre| P1

    MDB --> P1
    P1 --> PV
    PV --> PC
    PC --> PG

    MDB --> R1 --> IDX --> R2
```

---

## 2. Flux de données détaillé

```mermaid
flowchart LR
    subgraph INGEST ["Ingestion"]
        I1[4_bootstrap_data.py\nrecherche mots-clés + domaines]
        I2[3_job_bluesky_to_mongo.py\ntimeline personnelle]
    end

    subgraph NLP ["nlp_cleaning (Kedro)"]
        N1[fetch_from_mongo\nExtraction MongoDB]
        N2[clean_posts\nlowercase · suppr. URLs\nmentions · hashtags]
    end

    subgraph VEC ["vectorization (Kedro)"]
        V1[vectorize_posts\nTF-IDF · 5 000 features\nn-grammes 1-2]
    end

    subgraph CLS ["classification (Kedro)"]
        C1[add_emotion_features\nVADER : neg/neu/pos/compound]
        C2[fetch_labels_from_mongo\nreliable / unreliable]
        C3[train_classifier\nLogistic Regression]
        C4[save_to_postgres]
    end

    subgraph OUT ["Sorties"]
        O1[(classification_results\nPostgreSQL)]
    end

    I1 & I2 --> MDB[(MongoDB\nBluesky.timeline)]
    MDB --> N1 --> N2

    N2 -->|cleaned_bluesky_posts.parquet| V1
    V1 -->|vectorized_posts.parquet| C1
    MDB --> C2
    C1 --> C3
    C2 --> C3
    C3 --> C4 --> O1
```

---

## 3. Pipeline de classification Kedro (détail)

```mermaid
flowchart TD
    A[Post Bluesky — texte brut] --> B[NLP Cleaning\nlowercase · suppr. URLs\nmentions · hashtags]
    B --> V[TF-IDF\n5 000 features · n-grammes 1-2]
    B --> E[VADER\nneg / neu / pos / compound]

    subgraph Train ["Entraînement supervisé (MongoDB)"]
        D[source_label MongoDB\nreliable / unreliable\nvia 5_label_sources.py]
        LR[Logistic Regression\nclass_weight=balanced]
        D --> LR
    end

    V --> LR
    E --> LR
    LR --> F[predict_proba]
    F --> G[reliability_score\nfloat entre 0.0 et 1.0]

    G -->|score ≥ 0.5| H[✅ reliable]
    G -->|score < 0.5| J[❌ unreliable]

    G --> K[(classification_results\nPostgreSQL)]
```

---

## 4. Méthode TF-IDF + VADER + Régression Logistique — Explication

### 4.1 TF-IDF — Représentation lexicale

Chaque post nettoyé est transformé en vecteur creux de fréquences de mots/bigrammes
pondérées (5 000 features max, `sklearn.feature_extraction.text.TfidfVectorizer`).

### 4.2 VADER — Intensité émotionnelle

`vaderSentiment` donne 4 scores par texte (`neg`, `neu`, `pos`, `compound`).
Hypothèse : les fake news ont souvent un registre plus chargé émotionnellement
(indignation, alarmisme) que la presse fiable — ces 4 scores sont concaténés
aux features TF-IDF.

### 4.3 Régression Logistique — Classification binaire

La **Logistic Regression** (scikit-learn, `class_weight="balanced"` pour compenser
le déséquilibre reliable/unreliable) prend le vecteur TF-IDF + émotion en entrée et
produit une probabilité d'appartenance à la classe "reliable".

```
score = P(classe = "reliable" | features)
      = σ(W · features + b)
```

**Inférence (prédiction sur un nouveau texte)** — voir `scripts/test_single_news.py` :

```mermaid
flowchart LR
    T[Texte brut] --> C[Nettoyage\nclean_text]
    C --> TF[TF-IDF transform]
    C --> EM[VADER polarity_scores]
    TF --> LR[Logistic Regression\npredict_proba]
    EM --> LR
    LR --> S[score = P reliable\n0.0 → 1.0]
    S -->|≥ 0.5| R[✅ reliable]
    S -->|< 0.5| U[❌ unreliable]
```

---

## 5. RAG — Fact-checker interactif (frontend)

Système **indépendant** du pipeline Kedro ci-dessus, utilisé par `frontend/app.py` :

1. `10_build_rag_index.py` encode tous les posts MongoDB `reliable` avec MiniLM
   (`paraphrase-multilingual-MiniLM-L12-v2`, 384 dims) et sauvegarde l'index dans
   `pipeline-kedro/data/06_models/rag_index.npy`.
2. `rag_service.py` (`RAGCredibilityService`) charge cet index, retrouve les
   articles les plus proches sémantiquement d'une news donnée (similarité cosinus),
   complète avec une recherche web (DuckDuckGo / Wikipédia) sur des domaines fiables,
   puis envoie les deux contextes à **Mistral** pour obtenir un score de
   crédibilité (0-100) + justification + alignement (confirmé/contredit/non couvert).
3. `11_rag_credibility.py` : interface CLI. `frontend/app.py` : interface Streamlit.

---

## 6. DAG Airflow — Orchestration

```mermaid
flowchart LR
    A([START\ntoutes les 30 min]) --> B

    B[ingestion_mongo\nscript 3] --> C

    C[nlp_cleaning\nkedro run] --> D

    D[vectorization\nkedro run] --> E[classification\nkedro run] --> F[reporting\nkedro run] --> G([END])
```

---

## 7. Structure des fichiers du projet

```
Projet-d-etude-SUPDEVINCI-2025-2026/
│
├── scripts/                          ← Scripts d'ingestion, ML et RAG
│   ├── 1_code_token.py               Authentification Bluesky → token.json
│   ├── 2_Mongodb_Connection.py       Test de connexion MongoDB Atlas
│   ├── 3_job_bluesky_to_mongo.py     Ingestion timeline → MongoDB
│   ├── 4_bootstrap_data.py           Collecte massive par mots-clés/domaines
│   ├── 5_label_sources.py            Labellisation domaines (reliable/unreliable)
│   ├── 5b_purge_unlabeled.py         Supprime les posts "unknown" de MongoDB
│   ├── 6_nlp_cleaning.py             Lance kedro run --pipeline nlp_cleaning
│   ├── 7_vectorization.py            Lance kedro run --pipeline vectorization
│   ├── 8_classification.py           Lance kedro run --pipeline classification
│   ├── 9_reporting.py                Lance kedro run --pipeline reporting
│   ├── 10_build_rag_index.py         Construit l'index MiniLM (RAG)
│   ├── 11_rag_credibility.py         CLI : score de crédibilité RAG + Mistral
│   ├── bluesky_api.py                Client API Bluesky (timeline + recherche)
│   ├── mongo_service.py              Service MongoDB (upsert bulk)
│   ├── rag_service.py                RAGCredibilityService (Mongo + Web + Mistral)
│   ├── web_search_service.py         Recherche web (DuckDuckGo/Wikipédia)
│   ├── test_news.py / test_single_news.py  Inférence locale du modèle classification
│
├── frontend/
│   └── app.py                        Interface Streamlit du fact-checker (RAG)
│
├── pipeline-kedro/                   ← Pipeline ML batch (Kedro 1.0)
│   ├── conf/base/
│   │   ├── catalog.yml               Datasets Kedro (parquet, pickle, postgres)
│   │   ├── parameters_classification.yml  test_size, class_weight
│   │   ├── parameters_nlp_cleaning.yml    filtres de nettoyage
│   │   └── parameters_vectorization.yml   max_features, ngram_range
│   ├── data/
│   │   ├── 02_intermediate/  cleaned_bluesky_posts.parquet
│   │   ├── 04_feature/       vectorized_posts.parquet, posts_with_emotion.parquet
│   │   └── 06_models/        classifier_model.pickle, tfidf_vectorizer.pickle,
│   │                         rag_index.npy (versionnés)
│   └── src/pipeline_kedro/pipelines/
│       ├── nlp_cleaning/     fetch_from_mongo · clean_posts
│       ├── vectorization/    TF-IDF 5 000 features
│       └── classification/   add_emotion_features · train_classifier · save_to_postgres
│
├── airflow/dags/
│   └── bluesky_sync_dag.py           DAG toutes les 30 min
│
├── docker-compose.yml                PostgreSQL · Airflow · services
├── monitoring/prometheus.yml         Métriques Prometheus
├── docs/                             Cahier des charges · explications
├── structure/architecture.md         ← Ce fichier
└── .env                              MONGO_URI · BSKY_IDENTIFIER · BSKY_PASSWORD · MISTRAL_API_KEY
```

---

## 8. Labels de fiabilité — règle de décision

```mermaid
flowchart TD
    S[source_label\nscript 5_label_sources.py]

    S -->|domaine connu fiable\nreuters.com · bbc.com · apnews.com\nwho.int · nature.com · lemonde.fr| R[reliable]
    S -->|domaine connu non fiable\ninfowars.com · rt.com\nnaturalnews.com| U[unreliable]
    S -->|domaine inconnu ou\npas d'URL externe| K[unknown]

    R & U -->|supervision pour l'entraînement| ML[Logistic Regression\npipeline classification]
    R -->|corpus de référence| RAG[Index MiniLM\nRAG]
    K -->|scoring en inférence uniquement| ML

    ML --> SCORE[reliability_score: 0.0 → 1.0]
```

---

## 9. Ordre d'exécution complet

```mermaid
flowchart TD
    A[python 1_code_token.py\nAuthentification Bluesky] --> B
    B[python 4_bootstrap_data.py\nCollecte des posts] --> C
    C[python 5_label_sources.py\nLabellisation reliable/unreliable] --> D
    D[python 5b_purge_unlabeled.py\nNettoyage des posts unknown] --> E
    E[python 6_nlp_cleaning.py\nKedro nlp_cleaning] --> F
    F[python 7_vectorization.py\nKedro vectorization] --> G[python 8_classification.py\nKedro classification]
    G --> H[python 9_reporting.py]

    C --> I[python 10_build_rag_index.py\nIndex MiniLM des sources fiables]
    I --> J[python 11_rag_credibility.py\nou streamlit run frontend/app.py]

    style A fill:#e8f4fd
    style G fill:#d5f5e3
    style J fill:#d5f5e3
```
