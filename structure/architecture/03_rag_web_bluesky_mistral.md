# Diagramme 3 — RAG Web + RAG Bluesky + Mistral

Détaille le cœur du fact-checking : la combinaison de deux sources de contexte
(base Bluesky labellisée via index MiniLM + recherche web temps réel sur sources
fiables) plus l'analyse sémantique locale, le tout synthétisé par Mistral AI pour
produire un score de crédibilité.

```mermaid
flowchart TD
    QUERY["Texte de la news à vérifier"]
    CLASSIF["Analyse sémantique locale<br/>(Diagramme 2) : score + label"]

    subgraph BUILD["Préparation de l'index (hors-ligne)"]
        direction TB
        FETCHREL["10_build_rag_index.py<br/>docs source_label = reliable"]
        ENCODE["MiniLM<br/>paraphrase-multilingual-L12<br/>(384 dims)"]
        NORM["normalisation L2"]
        IDXFILE["rag_index.npy<br/>embeddings + métadonnées"]
        FETCHREL --> ENCODE --> NORM --> IDXFILE
    end

    subgraph R1["RAG Bluesky (base locale)"]
        direction TB
        EMBQ["encode(query)<br/>MiniLM + L2"]
        COS["cosine_similarity<br/>vs index"]
        TOPK["top-K articles<br/>+ similarité"]
        EMBQ --> COS --> TOPK
    end

    subgraph R2["RAG Web (temps réel)"]
        direction TB
        DDGNEWS["DDGS.news<br/>(résultats datés)"]
        DDGTXT["DDGS.text<br/>(complément)"]
        FILTER["Filtre domaines de confiance<br/>+ tri du + récent au + ancien"]
        DDGNEWS --> FILTER
        DDGTXT --> FILTER
    end

    subgraph SYNTH["Synthèse Mistral"]
        direction TB
        PROMPT["Construction du prompt<br/>4 sources priorisées :<br/>web &gt; Bluesky &gt; sémantique &gt; similarité"]
        LLM["mistral-small-latest<br/>chat.complete"]
        PARSE["Extraction JSON<br/>score · label · alignment · justification"]
        PROMPT --> LLM --> PARSE
    end

    RESULT["Résultat de crédibilité<br/>0-100 · fiable/suspect/non fiable"]

    IDXFILE --> COS
    QUERY --> EMBQ
    QUERY --> DDGNEWS
    QUERY --> DDGTXT

    TOPK --> PROMPT
    FILTER --> PROMPT
    CLASSIF --> PROMPT
    PARSE --> RESULT

    subgraph UI["Restitution (Streamlit)"]
        direction TB
        GAUGE["Jauge + verdict"]
        COLB["Colonne Posts Bluesky"]
        COLW["Colonne Articles de presse"]
        WIKI["Mots cliquables → Wikipédia"]
    end

    RESULT --> GAUGE
    TOPK --> COLB
    FILTER --> COLW
    QUERY --> WIKI
```

## Règles de scoring (appliquées par Mistral)

| Alignement avec les sources | Plage de score | Label |
|---|---|---|
| Confirmée | 70 – 100 | `reliable` (✅ Fiable) |
| Peu couverte / ambiguë | 40 – 69 | `suspect` (⚠️ À vérifier) |
| Contredite | 0 – 39 | `unreliable` (❌ Non fiable) |

**Pondération** : articles web récents > posts Bluesky vérifiés > analyse
sémantique locale > similarité générale. Un style jugé suspect par l'analyse
sémantique (< 75 %) peut faire baisser le score jusqu'à −20 points, surtout
lorsque la couverture factuelle est faible.
