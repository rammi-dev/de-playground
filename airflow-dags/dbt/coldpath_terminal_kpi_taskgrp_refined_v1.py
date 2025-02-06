from datetime import datetime
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
coldpath_source_root_dir = Variable.get("coldpath_root").strip('"')
pkf_alarms_s3_path = Variable.get("pkf_alarms_s3_path").strip('"')
sss_alarms_s3_path = Variable.get("sss_alarms_s3_path").strip('"')

 # trino_conn_prms.login,
dbt_env_vars = {
        "TRINO_USER": trino_conn_prms.login,
        "TRINO_PASSWD": trino_conn_prms.password,
        "TRINO_HOST": trino_conn_prms.host,
        "TRINO_PORT": f'"{trino_conn_prms.port}"',
        "USER_SCHEMA": trino_conn_prms.schema,
        "S3_ENDPOINT": f'"{coldpath_s3_endpoint}"',
        "HIVE_CATALOG": 'hive',
        "COLDPATH_ROOT ": coldpath_source_root_dir,
        "PKF_ALARMS_S3_PATH": f'{coldpath_s3_endpoint}/{pkf_alarms_s3_path}',
        "SSS_ALARMS_S3_PATH": f'{coldpath_s3_endpoint}/{sss_alarms_s3_path}',
    }

render_config_asset = RenderConfig(
    # dbt_executable_path="DBT_EXECUTABLE_PATH", 
    select=["tag:refined"],  # Only include models with the specific tag
    exclude=[],            # Exclude models if needed
    selector=None,         # Optional: Use a DBT YAML selector if defined
)

execution_config=ExecutionConfig(
        dbt_executable_path=Path(DBT_EXECUTABLE_PATH)
        )

# Default arguments for the DAG
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
}

@dag(
    dag_id="dbt_termianl_taskgroup_refined",
    default_args=default_args,
    description="run asset",
    schedule_interval="5 0 * * *",  
    start_date=datetime(2025, 1, 28),
    catchup=False,
    tags=['cold-path'] , # Add tags for grouping
    max_active_runs=1,  
)
def terminal_kpi_refined_dbt_dag():

    # env variable raw_selected_datetime sent to DBT 
    # for incemental laod
    # logical date defined in {{ ts }} will be passed to DBT
    
    dbt_env_partition = {
        "PROCESSING_DATETIME__asset": "{{ ds }}",
    }

    vars = dbt_env_vars | dbt_env_partition
    print(vars)
    # TaskGroup for DBT
    transform_asset = DbtTaskGroup(
        group_id="transform_asset",
        project_config=ProjectConfig(dbt_project_path=DBT_PROJECT_PATH,
                                     manifest_path=DBT_MANIFEST_PATH
                                    ),
        profile_config = ProfileConfig(profile_name="datahub",
                                       target_name="dev",
                                       profiles_yml_filepath=DBT_PROFILE_PATH
                                      ),
        execution_config=execution_config,
        render_config=render_config_asset,
        operator_args={
            "env": vars,
        },
        default_args={"retries": 2},
    )

    # Define task dependencies
    transform_asset

terminal_kpi_refined_dbt_dag()