from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="GetAPITomongodb",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule_interval="*/30 * * * *",  # Déclenchement automatique toutes les 30 minutes
    catchup=False,
    tags=["python", "script"],
) as dag:

    # ÉTAPE 1 : Récupérer les posts depuis Bluesky et les insérer dans MongoDB
    run_script = BashOperator(
        task_id="run_python_script",
        bash_command="python /opt/airflow/scripts/get_api_to_mongodb.py"
    )

    # ÉTAPE 2 : Une fois la donnée ingérée, lancer Kedro pour nettoyer et générer la matrice TF-IDF
    run_kedro = BashOperator(
        task_id="run_kedro_pipeline",
        bash_command="cd /opt/airflow/pipeline-kedro && kedro run --pipeline vectorization"
    )

    # ORDRE D'EXÉCUTION : D'abord l'ingestion, puis le traitement Kedro
    run_script >> run_kedro