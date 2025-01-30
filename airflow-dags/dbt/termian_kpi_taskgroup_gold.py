from datetime import datetime
from airflow.decorators import dag
from airflow.operators.python import PythonOperator
from cosmos import DbtDag, DbtTaskGroup, ExecutionMode, InvocationMode, LoadMode, ProjectConfig, ExecutionConfig, ProfileConfig, RenderConfig
from airflow.models import Variable
from cosmos.profiles.trino import TrinoBaseProfileMapping
from pathlib import Path
from cosmos.profiles import TrinoLDAPProfileMapping
import os
# from airflow.utils.log.logging_mixin import LoggingMixin

# Define paths
VENV_PATH = "/opt/airflow/src/dbt-env/bin/activate"

DBT_PROJECT_PATH = f"{os.environ['AIRFLOW_HOME']}/src/dags/models_cold/dbt_model/src"
# in the virtual environment created in the Dockerfile
DBT_EXECUTABLE_PATH = f"{os.environ['AIRFLOW_HOME']}/venv/bin/run-dbt.sh"
DBT_VENV_PATH = f"{os.environ['AIRFLOW_HOME']}/src/dbt-env"
DBT_TARGET_PATH = "/opt/airflow/src/dbt-targets"
DBT_MANIFEST_PATH = "/opt/airflow/src/dags/models_cold/dbt_model/src/target/manifest.json"

# Create a logger instance
# logger = LoggingMixin().log

dbt_env_vars = {
        "TRINO_USER": Variable.get("trino_user", default_var="your-user"),
        "TRINO_PASSWD": Variable.get("trino_passwd", default_var="your pass"),
        "TRINO_HOST": Variable.get("trino_host", default_var="trino.data.hub.flowbird.cloud"),
        "TRINO_PORT": Variable.get("trino_port", default_var="443"),
        "HIVE_CATALOG": Variable.get("hive_catalog", default_var="hive"),
        "USER_SCHEMA": Variable.get("user_schema", default_var="kmikolajczyk"),
        "S3_ENDPOINT": Variable.get("s3_endpoint", default_var="s3a://hpf-datahub-pipeline-dev/"),
        "PKF_ALARMS_TOPIC": Variable.get("pkf_alarms_topic", default_var="dev.hpf-datahub-pipeline.parkfolio-nyc-alarms"),
        "SSS_ALARMS_TOPIC": Variable.get("sss_alarms_topic", default_var="dev.hpf-datahub-pipeline.sss-nyc-alarms"),
        "PKF_ALARMS_S3_PATH": Variable.get(
            "pkf_alarms_s3_path",
            default_var="s3a://hpf-datahub-pipeline-dev/topics/dev.hpf-datahub-pipeline.parkfolio-nyc-alarms/",
        ),
        "SSS_ALARMS_S3_PATH": Variable.get(
            "sss_alarms_s3_path",
            default_var="s3a://hpf-datahub-pipeline-dev/topics/dev.hpf-datahub-pipeline.sss-nyc-alarms/",
        ),
        "PATH":"/opt/airflow/src/dbt-env/bin",
    }

render_config_gold = RenderConfig(
    dbt_executable_path="DBT_EXECUTABLE_PATH", 
    select=["tag:terminal_kpi_gold"],  # Only include models with the specific tag
    exclude=[],            # Exclude models if needed
    selector=None,         # Optional: Use a DBT YAML selector if defined
)

execution_config=ExecutionConfig(
        dbt_executable_path=Path(DBT_EXECUTABLE_PATH)
        )

profile_config = ProfileConfig(
    profile_name="datahub",
    target_name="dev",
    profiles_yml_filepath="/opt/airflow/src/dags/models_cold/dbt_model/profiles.yml"
)

# Default arguments for the DAG
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
}

@dag(
    dag_id="dbt_virtual_taskgroup_gold",
    default_args=default_args,
    description="run gold",
    schedule_interval="5 0 * * *",  
    start_date=datetime(2025, 1, 28),
    catchup=True,
    tags=['cold-path'] , # Add tags for grouping
    max_active_runs=1,  
)
def my_simple_dbt_dag():
    dbt_env_partition = {
        "partition_inc": "{{ ts }}",
    }

    vars = dbt_env_vars | dbt_env_partition

    # TaskGroup for DBT
    transform_gold = DbtTaskGroup(
        group_id="transform_gold",
        project_config=ProjectConfig(dbt_project_path=DBT_PROJECT_PATH,
                                     manifest_path=DBT_MANIFEST_PATH
                                    ),
        profile_config = ProfileConfig(profile_name="datahub",
                                       target_name="dev",
                                       profiles_yml_filepath="/opt/airflow/src/dags/models_cold/dbt_model/profiles.yml"
                                      ),
        execution_config=execution_config,
        render_config=render_config_gold,
        operator_args={
            "env": vars,
        },
        default_args={"retries": 2},
    )

    # Define task dependencies
    transform_gold

my_simple_dbt_dag()