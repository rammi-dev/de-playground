from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.models import Variable
from airflow.hooks.base import BaseHook
from datetime import datetime
import os


AIRFLOW_HOME=f"{os.environ['AIRFLOW_HOME']}"

DBT_PROJECT_DIR = f"{AIRFLOW_HOME}/src/dags/models_cold/dbt_model/src"
DBT_PROFILE_PATH= f"{AIRFLOW_HOME}/src/dags/models_cold/dbt_model" # TODO parametrize
DBT_VEVN_PATH = Variable.get("coldpath_dbt_venv").strip('"')

# in the virtual environment created in the Dockerfile
DBT_VENV_PATH = f"{AIRFLOW_HOME}/{DBT_VEVN_PATH}/"
DBT_EXECUTABLE = f"{DBT_VENV_PATH}/bin/dbt"

trino_conn_prms = BaseHook.get_connection("trino_coldpath")
coldpath_s3_endpoint = Variable.get("coldpath_s3_endpoint").strip('"')
coldpath_root_folder = Variable.get("coldpath_root").strip('"')
coldpath_source_root_dir = Variable.get("coldpath_root").strip('"')
pkf_alarms_s3_path = Variable.get("pkf_alarms_s3_path").strip('"')
sss_alarms_s3_path = Variable.get("sss_alarms_s3_path").strip('"')

DBT_ENV_VARS = {
        "TRINO_USER": trino_conn_prms.login,
        "TRINO_PASSWD": trino_conn_prms.password,
        "TRINO_HOST": trino_conn_prms.host,
        "TRINO_PORT": f'"{trino_conn_prms.port}"',
        "USER_SCHEMA": trino_conn_prms.schema,
        "S3_ENDPOINT": coldpath_s3_endpoint,
        "HIVE_CATALOG": 'hive',
        "DBT_PROFILE_PATH": DBT_PROFILE_PATH,
        "DBT_PROJECT_DIR": DBT_PROJECT_DIR,
        "COLDPATH_ROOT ": coldpath_source_root_dir,
        "PKF_ALARMS_S3_PATH": f'{coldpath_s3_endpoint}/{pkf_alarms_s3_path}',
        "SSS_ALARMS_S3_PATH": f'{coldpath_s3_endpoint}/{sss_alarms_s3_path}',
    }

# Default arguments for the DAG
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2024, 2, 6),
    "retries": 1,
}

# Define the DAG
with DAG(
    dag_id="cp_dbt_termianal_kpi_refined_v1",
    default_args=default_args,
    description="Run DBT bash in a virtual environment via bash",
    schedule_interval="0 1 * * *",  # Runs daily at 1 AM
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['cold-path'] , # Add tags for grouping
    max_active_runs=1, 
) as dag:

    DBT_ENV_PARTITION = {
        "PROCESSING_DATETIME__GOLD": "{{ ts }}",
    }

    vars = DBT_ENV_VARS | DBT_ENV_PARTITION

    wait_task = ExternalTaskSensor(
        task_id="wait_for_task_cp_dbt_termian_kpi_asset_task",
        external_dag_id="cp_dbt_termianal_kpi_asset_v1",
        external_task_id="cp_dbt_termian_kpi_asset_task",
        execution_date_fn=lambda dt: dt.replace(hour=23, minute=0, second=0),  # Wait for the last hourly run
        mode="poke",
        timeout=3600,  # Wait up to 1 hour
    )

    # Define the dbt run task
    dbt_run = BashOperator(
        task_id="cp_dbt_termian_kpi_refined_task",
        bash_command="""
        TS="{{ ts_nodash }}" 
        TEMP_DIR="/tmp/cp_dbt_termian_kpi_refined_task_$TS"
        
        # Ensure cleanup happens on any exit (success, failure, or termination)
        trap 'rm -rf $TEMP_DIR; echo "Deleted temporary directory: $TEMP_DIR"' EXIT SIGINT SIGTERM
        
        # Create temporary directory
        mkdir -p $TEMP_DIR 
        echo "Using temporary target directory: $TEMP_DIR"
    
        # Run dbt with the project reference
        {DBT_EXECUTABLE} run --profiles-dir {DBT_PROFILE_PATH} --select tag:asset 
        """.replace("{DBT_EXECUTABLE}", DBT_EXECUTABLE)
           .replace("{DBT_PROFILE_PATH}",  DBT_PROFILE_PATH),
        env=DBT_ENV_VARS, 
        )
    
    wait_task >> dbt_run
