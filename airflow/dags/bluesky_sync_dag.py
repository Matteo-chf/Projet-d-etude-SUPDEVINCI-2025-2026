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
    dag_id="bluesky_pipeline",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule_interval="*/30 * * * *",
    catchup=False,
    tags=["bluesky", "kedro"],
) as dag:

    ingest = BashOperator(
        task_id="ingestion_mongo",
        bash_command="python /opt/airflow/scripts/3_job_bluesky_to_mongo.py"
    )

    nlp_cleaning = BashOperator(
        task_id="nlp_cleaning",
        bash_command="cd /opt/airflow/pipeline-kedro && kedro run --pipeline nlp_cleaning"
    )

    vectorization = BashOperator(
        task_id="vectorization",
        bash_command="cd /opt/airflow/pipeline-kedro && kedro run --pipeline vectorization"
    )

    reporting = BashOperator(
        task_id="reporting",
        bash_command="cd /opt/airflow/pipeline-kedro && kedro run --pipeline reporting"
    )

    ingest >> nlp_cleaning >> vectorization >> reporting
