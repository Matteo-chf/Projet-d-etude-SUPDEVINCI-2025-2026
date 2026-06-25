# Diagramme 1 — Architecture globale & chaîne d'ingestion

Ce diagramme couvre l'ensemble de la plateforme à haut niveau, puis détaille la
chaîne d'ingestion : **connexion à l'API Bluesky → bootstrap → labelisation →
purge des non-labellisés → nettoyage NLP**.

---

## 1.1 Vue d'ensemble de la plateforme

```mermaid
flowchart LR
    subgraph SOURCES["Sources externes"]
        direction TB
        BSKY["API Bluesky<br/>(AT Protocol)"]
        WEB["Web<br/>(DuckDuckGo / Wikipedia)"]
        MISTRAL["API Mistral AI"]
    end

    subgraph INGEST["Ingestion &amp; préparation"]
        direction TB
        COLLECT["Collecte<br/>scripts 1 à 4"]
        LABEL["Labelisation<br/>script 5 / 5b"]
        CLEAN["Nettoyage NLP<br/>Kedro"]
    end

    subgraph ML["Apprentissage &amp; index"]
        direction TB
        VECT["Vectorisation TF-IDF<br/>+ Classification"]
        RAGIDX["Index RAG<br/>MiniLM (.npy)"]
    end

    subgraph STORE["Stockage"]
        direction TB
        MONGO[("MongoDB<br/>Bluesky.timeline")]
        PG[("PostgreSQL<br/>classification_results")]
    end

    subgraph SERVE["Service &amp; restitution"]
        direction TB
        RAGSVC["Service RAG<br/>de crédibilité"]
        UI["Frontend Streamlit<br/>Fact-Checker IA"]
    end

    ORCH["Orchestration<br/>Airflow (DAG /30 min)"]

    BSKY --> COLLECT --> MONGO
    MONGO --> LABEL --> MONGO
    MONGO --> CLEAN --> VECT
    VECT --> PG
    VECT --> RAGIDX
    MONGO --> RAGIDX

    UI --> RAGSVC
    RAGSVC --> RAGIDX
    RAGSVC --> WEB
    RAGSVC --> MISTRAL
    RAGSVC --> UI

    ORCH -.pilote.-> COLLECT
    ORCH -.pilote.-> CLEAN
    ORCH -.pilote.-> VECT
```

---

## 1.2 Chaîne d'ingestion détaillée

De l'authentification jusqu'au texte nettoyé prêt pour la vectorisation.

```mermaid
flowchart TD
    START(["Démarrage du pipeline d'ingestion"])

    subgraph S1["Étape 1 — Authentification"]
        direction TB
        ENV1["Identifiants .env<br/>BSKY_IDENTIFIER / BSKY_PASSWORD"]
        LOGIN["1_code_token.py<br/>createSession (AT Protocol)"]
        TOKEN["token.json<br/>accessJwt + refreshJwt"]
        ENV1 --> LOGIN --> TOKEN
    end

    subgraph S2["Étape 2 à 4 — Collecte des posts"]
        direction TB
        KW["Mots-clés génériques<br/>+ domaines non fiables"]
        BOOT["4_bootstrap_data.py<br/>searchPosts paginé"]
        TL["3_job_bluesky_to_mongo.py<br/>getTimeline"]
        UPSERT["mongo_service.insert_timeline<br/>upsert sur 'uri' (anti-doublon)"]
        KW --> BOOT --> UPSERT
        TL --> UPSERT
    end

    MONGO[("MongoDB<br/>collection timeline")]

    subgraph S5["Étape 5 — Labelisation"]
        direction TB
        SIG1["Signal fort : handle vérifié<br/>(DNS Bluesky)"]
        SIG2["Signal secondaire : domaine<br/>du lien partagé"]
        DEC{"Domaine connu ?"}
        REL["source_label = reliable"]
        UNREL["source_label = unreliable"]
        UNK["source_label = unknown"]
        SIG1 --> DEC
        SIG2 --> DEC
        DEC -->|domaine de confiance| REL
        DEC -->|domaine non fiable| UNREL
        DEC -->|aucun signal| UNK
    end

    subgraph S5B["Étape 5b — Purge"]
        direction TB
        PURGE["5b_purge_unlabeled.py<br/>delete_many"]
        KEEP["Conserve uniquement<br/>reliable + unreliable"]
        PURGE --> KEEP
    end

    subgraph S6["Étape 6 — Nettoyage NLP (Kedro)"]
        direction TB
        FETCH["fetch_from_mongo<br/>extraction multi-format"]
        CT["clean_posts<br/>minuscules · sans URL/@/#<br/>sans ponctuation"]
        CLEANED["cleaned_bluesky_posts<br/>(Parquet)"]
        FETCH --> CT --> CLEANED
    end

    START --> S1
    TOKEN --> S2
    S2 --> MONGO
    MONGO --> S5
    REL --> MONGO
    UNREL --> MONGO
    UNK --> MONGO
    MONGO --> S5B
    KEEP --> MONGO
    MONGO --> S6
    CLEANED --> NEXT(["→ Vectorisation (Diagramme 2)"])
```
