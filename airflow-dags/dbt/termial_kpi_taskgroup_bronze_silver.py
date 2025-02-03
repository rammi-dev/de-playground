from datetime import datetime
from airflow import DAG
from airflow.decorators import dag
from cosmos import DbtTaskGroup, ProjectConfig, ExecutionConfig, ProfileConfig, RenderConfig
from airflow.models import Variable
from pathlib import Path
from airflow.hooks.base import BaseHook
import os

AIRFLOW_HOME=f"{os.environ['AIRFLOW_HOME']}"

DBT_PROJECT_PATH = f"{AIRFLOW_HOME}/src/dags/models_cold/dbt_model/src"
DBT_PROFILE_PATH="/opt/airflow/src/dags/models_cold/dbt_model/profiles.yml" # TODO parametrize
DBT_VEVN_PATH = Variable.get("coldpath_dbt_venv").strip('"')

# in the virtual environment created in the Dockerfile
DBT_VENV_PATH = f"{AIRFLOW_HOME}/{DBT_VEVN_PATH}/"
DBT_EXECUTABLE_PATH = f"{DBT_VENV_PATH}/bin/dbt"
DBT_MANIFEST_PATH = f"{AIRFLOW_HOME}/src/dags/models_cold/dbt_model/src/target/manifest.json"

trino_conn_prms = BaseHook.get_connection("trino_coldpath")
coldpath_s3_endpoint = Variable.get("coldpath_s3_endpoint")
coldpath_root_folder = Variable.get("coldpath_root_folder")
coldpath_hive_calalog = Variable.get("coldpath_hive_catalog")

 # trino_conn_prms.login,
dbt_env_vars = {
        "TRINO_USER": trino_conn_prms.login,
        "TRINO_PASSWD": trino_conn_prms.password,
        "TRINO_HOST": trino_conn_prms.host,
        "TRINO_PORT": f'"{trino_conn_prms.port}"',
        "USER_SCHEMA": trino_conn_prms.schema,
        "S3_ENDPOINT": coldpath_s3_endpoint,
        "HIVE_CATALOG": 'hive',
        "PKF_ALARMS_TOPIC": "dev.hpf-datahub-pipeline.parkfolio-nyc-alarms",
        "SSS_ALARMS_TOPIC": "dev.hpf-datahub-pipeline.sss-nyc-alarms",
        "PKF_ALARMS_S3_PATH": Variable.get(
            "pkf_alarms_s3_path",
            default_var="s3a://hpf-datahub-pipeline-dev/topics/dev.hpf-datahub-pipeline.parkfolio-nyc-alarms/",
        ),
        "SSS_ALARMS_S3_PATH": Variable.get(
            "sss_alarms_s3_path",
            default_var="s3a://hpf-datahub-pipeline-dev/topics/dev.hpf-datahub-pipeline.sss-nyc-alarms/",
        ),
    }

execution_config=ExecutionConfig(
        dbt_executable_path=Path(DBT_EXECUTABLE_PATH)
        )

profile_config = ProfileConfig(
    profile_name="datahub",
    target_name="dev",
    profiles_yml_filepath="/opt/airflow/src/dags/models_cold/dbt_model/profiles.yml"
)

render_config_bronze = RenderConfig(
    dbt_executable_path="DBT_EXECUTABLE_PATH", 
    select=["tag:raw"],  # Only include models with the specific tag
    exclude=[],            # Exclude models if needed
    selector=None,         # Optional: Use a DBT YAML selector if defined
)

render_config_silver = RenderConfig(
    dbt_executable_path="DBT_EXECUTABLE_PATH", 
    # load_method=LoadMode.DBT_LS,
    select=["tag:asset"],  # Only include models with the specific tag
    exclude=[],            # Exclude models if needed
    selector=None,         # Optional: Use a DBT YAML selector if defined
)

# Default arguments for the DAG
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
}

# Define the DAG
with DAG(
    dag_id="dbt_termian_kpi_bronze_silver",
    default_args=default_args,
    description="Run DBT TaskGroup in a virtual environment",
    schedule_interval="5 * * * *",  # Runs every hour at HH:05
    start_date=datetime(2025, 1, 27),
    catchup=False,
    tags=['cold-path'] , # Add tags for grouping
    max_active_runs=1, 
) as dag:
    
    # env variable raw_selected_datetime sent to DBT 
    # for incemental laod
    # ratirion defined in {{ ts }} will be passed to DBT

    dbt_env_partition = {
        "raw_selected_datetime": "{{ ts }}",
    }

    vars = dbt_env_vars | dbt_env_partition

    # TaskGroup for DBT
    transform_bronze = DbtTaskGroup(
        group_id="transform_bronze",
        project_config=ProjectConfig(dbt_project_path=DBT_PROJECT_PATH,
                                    manifest_path=DBT_MANIFEST_PATH,
                                    ),
        profile_config = ProfileConfig(profile_name="datahub",
                                       target_name="dev",
                                       profiles_yml_filepath=DBT_PROFILE_PATH
                                      ),
        execution_config=execution_config,
        render_config=render_config_bronze,
        operator_args={
            "env": vars,
        },
        default_args={"retries": 2},
    )
    transform_bronze


    # TaskGroup for DBT
    transform_silver = DbtTaskGroup(
        group_id="transform_silver",
        project_config=ProjectConfig(dbt_project_path=DBT_PROJECT_PATH,
                                     manifest_path=DBT_MANIFEST_PATH,
                                    ),
        profile_config = ProfileConfig(profile_name="datahub",
                                       target_name="dev",
                                       profiles_yml_filepath=DBT_PROFILE_PATH
                                      ),
        execution_config=execution_config,
        render_config=render_config_silver,
        operator_args={
            "env": vars,
        },
        default_args={"retries": 2},
    )

    # Define task dependencies
    transform_bronze >> transform_silver
