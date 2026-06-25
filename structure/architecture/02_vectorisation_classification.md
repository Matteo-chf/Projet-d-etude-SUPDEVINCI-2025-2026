# Diagramme 2 — Vectorisation TF-IDF & Classification

Détaille les deux pipelines Kedro qui transforment le texte nettoyé en vecteurs
numériques, puis entraînent un classifieur de fiabilité. Les artefacts produits
(vectorizer + modèle) sont ensuite réutilisés par le frontend.

```mermaid
flowchart TD
    CLEANED["cleaned_bluesky_posts<br/>(sortie du nettoyage NLP)"]

    subgraph VEC["Pipeline 'vectorization'"]
        direction TB
        TFIDF["TfidfVectorizer<br/>max_features · ngram (1,2)<br/>min_df · sublinear_tf"]
        FIT["fit_transform<br/>sur cleaned_text"]
        VECDF["vectorized_posts<br/>matrice TF-IDF + métadonnées"]
        VECMODEL["tfidf_vectorizer.pickle<br/>(artefact réutilisable)"]
        TFIDF --> FIT --> VECDF
        FIT --> VECMODEL
    end

    subgraph CLF["Pipeline 'classification'"]
        direction TB
        EMO["add_emotion_features<br/>VADER : neg · neu · pos · compound"]
        FEAT["Features finales<br/>TF-IDF ⊕ scores émotionnels"]
        LBL["fetch_labels_from_mongo<br/>reliable / unreliable"]
        MERGE["merge sur 'uri'<br/>(jointure features ↔ labels)"]
        SPLIT["train_test_split<br/>stratifié · 80/20"]
        TRAIN["LogisticRegression<br/>class_weight = balanced"]
        SCORE["reliability_score<br/>+ predicted_label"]
        CLFMODEL["classifier_model.pickle<br/>(artefact réutilisable)"]

        EMO --> FEAT
        FEAT --> MERGE
        LBL --> MERGE
        MERGE --> SPLIT --> TRAIN
        TRAIN --> SCORE
        TRAIN --> CLFMODEL
    end

    MONGO[("MongoDB<br/>source_label")]
    PG[("PostgreSQL<br/>classification_results")]

    CLEANED --> TFIDF
    VECDF --> EMO
    MONGO --> LBL
    SCORE --> PG

    subgraph FRONT["Réutilisation côté frontend"]
        direction TB
        LOADV["get_classifier()<br/>charge les 2 pickles"]
        INPUT["Texte saisi par l'utilisateur"]
        CLASSIFY["classify_local()<br/>TF-IDF + VADER → proba"]
        VERDICT["Verdict sémantique<br/>reliable si score ≥ 75%, sinon suspect"]
        INPUT --> CLASSIFY
        LOADV --> CLASSIFY
        CLASSIFY --> VERDICT
    end

    VECMODEL --> LOADV
    CLFMODEL --> LOADV
    VERDICT -.transmis à Mistral.-> NEXT(["→ Service RAG (Diagramme 3)"])
```

## Notes

- **Features hybrides** : la classification ne se fonde pas uniquement sur le
  vocabulaire (TF-IDF) mais ajoute la charge émotionnelle (VADER), car les fausses
  informations présentent souvent un registre plus alarmiste.
- **Double usage du modèle** : entraîné côté pipeline (batch, sauvegarde dans
  PostgreSQL), il est rechargé en temps réel par le frontend pour scorer le texte
  saisi par l'utilisateur — sans nouvel entraînement.
- **Seuil** : le pipeline classe à 0,5 ; le frontend relève le seuil à **0,75**
  pour distinguer « fiable » d'un style simplement « suspect ».
