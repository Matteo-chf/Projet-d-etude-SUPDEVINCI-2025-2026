# Cahier des Charges & Déroulé des Interventions

## Contexte du Projet
Projet d'étude Master - Traitement de flux d'information (M2) appliqué à la détection de Fake News sur le réseau social **Bluesky**.
L'objectif est d'implémenter un pipeline de données complet, depuis l'ingestion jusqu'à l'analyse Machine Learning de catégorisation d'articles.

---

## 🏗 Architecture Déployée

1. **Ingestion (Sources)** : API Bluesky (réseau social concurrent de X/Twitter).
2. **Stockage Brut** : MongoDB (Base de données orientée documents NoSQL).
3. **Orchestration** : Apache Airflow (gère la récurrence des tâches d'ingestion et de déclenchement du traitement).
4. **Data Science / ML** : Kedro (structuration modulaire via Data Catalog, pipelines de nettoyage, et de vectorisation).

---

## 🛠 Liste des Actions Réalisées

### 1. Analyse Initiale & Audit
- Découverte du besoin métier via les fichiers `projet.pdf` et `suite_cours_ML_projet.pdf`.
- Audit du `pipeline-kedro/` existant : Identification d'un pipeline `nlp_cleaning` incomplet et mal relié, et d'un projet brouillon `bluesky-pipeline/` (abandonné au profit du principal).

### 2. Développement de la brique Machine Learning (TF-IDF)
- **Objectif** : Transformer du texte libre en nombres exploitables par une Intelligence Artificielle.
- Création du pipeline Kedro complet `vectorization` (`nodes.py`, `pipeline.py`).
- Paramétrage dynamique de l'algorithme TF-IDF (`max_features: 5000`).
- Ajout automatique du modèle (`tfidf_vectorizer.pickle`) et des données (`tfidf_matrix.parquet`) configurés dans le `catalog.yml` de Kedro.

### 3. Debugging et Fix de l'environnement Kedro
- Résolution du problème silencieux où Kedro ne listait pas les pipelines (réinstallation locale de l'environnement via `pip install -e .`).
- Correction des dépendances manquantes (résolution des erreurs liées à `matplotlib`, `plotly`, et `pickle` manquants dans `kedro-datasets`).
- Solution robuste face à la dépréciation du module MongoDB dans Kedro (v9.2.0) en passant le pipeline sur du Parquet intermédiaire via un script Python natif (`mongo_to_parquet.py`) branché sur MongoDB Atlas/Local.

### 4. Transformation de la source de données
- Accroissement massif des capacités volumétriques pour le modèle :
  - L'ingestion limitait initialement à la timeline locale de l'utilisateur (56 posts).
  - Modification du script Python principal `scripts/get_api_to_mongodb.py` pour attaquer l'API globale `searchPosts` avec le filtre `"news"`, par lots de `100` posts.
- Construction immédiate d'une vraie base (~1100 posts) via un script turbo (`bootstrap_data.py`).

### 5. Intégration Continue & Automatisation
- **Docker** : Ajout d'un pont de volume (Volume Mount) de `pipeline-kedro/` vers le conteneur Apache Airflow afin qu'ils partagent le même environnement.
- **Airflow DAG** (`bluesky_sync_dag.py`) : Chainage des événements. Airflow s'occupe dorénavant de deux tâches :
  1. Il exécute les scripts d'ingestion (Python vers Mongo).
  2. Il déclenche _immédiatement après_ la transformation data science via `kedro run --pipeline vectorization`.
- L'horloge interne exécute ce processus automatiquement toutes les 30 minutes.

### 6. Nettoyage et Organisation
- Nettoyage des fichiers erratiques à la racine pour les confiner dans le dossier nouveau `docs/`.
- Repurging des scripts python expérimentaux stockés par erreur dans le dossier `scripts/` (conservation exclusive des codes d'import, de connexion et d'orchestration).
- L'explication concrète mathématique du TF-IDF et de l'intérêt pour le projet a été insérée explicitement pour la restitution client.

---

## 📈 Résultats et État Actuel
- La plateforme capte les postes mondiaux de la thématique "news" en temps quasi réel.
- Le cycle de transformation vers KEDRO NLP et TF-IDF s'exécute sans friction.
- Matériau généré : Une base contenant à l'heure actuelle plus de **1100 posts** nettoyés et découpés en tokens (mots-clés), sous dimension de 5000 features métriques, prêts à être envoyés dans un K-Means ou Random Forest pour détecter des Fake News.
