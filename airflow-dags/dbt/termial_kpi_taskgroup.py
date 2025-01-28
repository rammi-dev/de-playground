from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from cosmos import DbtDag, DbtTaskGroup, ExecutionMode, InvocationMode, LoadMode, ProjectConfig, ExecutionConfig, ProfileConfig, RenderConfig
from airflow.models import Variable
from cosmos.profiles.trino import TrinoBaseProfileMapping
from pathlib import Path
from cosmos.profiles import TrinoLDAPProfileMapping
import os

# Define paths
VENV_PATH = "/opt/airflow/src/dbt-env/bin/activate"

DBT_PROJECT_PATH = f"{os.environ['AIRFLOW_HOME']}/src/dags/models_cold/dbt_model/src"
# in the virtual environment created in the Dockerfile
DBT_EXECUTABLE_PATH = f"{os.environ['AIRFLOW_HOME']}/venv/bin/run-dbt.sh"
DBT_VENV_PATH = f"{os.environ['AIRFLOW_HOME']}/src/dbt-env"
DBT_TARGET_PATH = "/opt/airflow/src/dbt-targets"

render_config_bronze = RenderConfig(
    dbt_executable_path="DBT_EXECUTABLE_PATH", 
    select=["tag:terminal_kpi_bronze"],  # Only include models with the specific tag
    exclude=[],            # Exclude models if needed
    selector=None,         # Optional: Use a DBT YAML selector if defined
)


render_config_silver = RenderConfig(
    dbt_executable_path="DBT_EXECUTABLE_PATH", 
    # load_method=LoadMode.DBT_LS,
    select=["tag:terminal_kpi_silver"],  # Only include models with the specific tag
    exclude=[],            # Exclude models if needed
    selector=None,         # Optional: Use a DBT YAML selector if defined
)
render_config_gold = RenderConfig(
    dbt_executable_path="DBT_EXECUTABLE_PATH", 
    # load_method=LoadMode.DBT_LS,
    select=["tag:terminal_kpi_gold"],  # Only include models with the specific tag
    exclude=[],            # Exclude models if needed
    selector=None,         # Optional: Use a DBT YAML selector if defined
)

execution_config=ExecutionConfig(
        # execution_mode=ExecutionMode.VIRTUALENV,
        # virtualenv_dir=Path(DBT_VENV_PATH),
        # execution_mode=ExecutionMode.VIRTUALENV,
        # invocation_mode=InvocationMode.SUBPROCESS,
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

# Define the DAG
with DAG(
    dag_id="dbt_virtual_taskgroup",
    default_args=default_args,
    description="Run DBT TaskGroup in a virtual environment",
    schedule_interval="@hourly",
    start_date=datetime(2025, 1, 27),
    catchup=False,
) as dag:

    dbt_env_vars = {
        "TRINO_USER": Variable.get("trino_user", default_var="kmikolajczyk"),
        "TRINO_PASSWD": Variable.get("trino_passwd", default_var="Begat-windward-rascal-common-chaperon"),
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
        "logical_date": "{{ ds }}",
        "year": "{{ ds[:4] }}",
        "month": "{{ ds[5:7] }}",   # Extract the month
        "day": "{{ ds[8:10] }}",    # Extract the day
        "hour": "{{ ts[11:13] }}",  # Extract the hour from timestamp
    }
    

    # TaskGroup for DBT
    transform_bronze = DbtTaskGroup(
        group_id="transform_bronze",
        project_config=ProjectConfig(dbt_project_path=DBT_PROJECT_PATH,
                                     env_vars=dbt_env_vars,
                                     dbt_vars=dbt_env_vars),
        profile_config = ProfileConfig(profile_name="datahub",
                                       target_name="dev",
                                       profiles_yml_filepath="/opt/airflow/src/dags/models_cold/dbt_model/profiles.yml"
                                      ),
        execution_config=execution_config,
        render_config=render_config_bronze,
        default_args={"retries": 2},
    )
    transform_bronze


    # TaskGroup for DBT
    transform_silver = DbtTaskGroup(
        group_id="transform_silver",
        project_config=ProjectConfig(dbt_project_path=DBT_PROJECT_PATH,
                                     env_vars=dbt_env_vars,
                                     dbt_vars=dbt_env_vars),
        profile_config = ProfileConfig(profile_name="datahub",
                                       target_name="dev",
                                       profiles_yml_filepath="/opt/airflow/src/dags/models_cold/dbt_model/profiles.yml"
                                      ),
        execution_config=execution_config,
        render_config=render_config_silver,
        default_args={"retries": 2},
    )

    # TaskGroup for DBT
    transform_gold = DbtTaskGroup(
        group_id="transform_gold",
        project_config=ProjectConfig(dbt_project_path=DBT_PROJECT_PATH,
                                     env_vars=dbt_env_vars,
                                     dbt_vars=dbt_env_vars),
        profile_config = ProfileConfig(profile_name="datahub",
                                       target_name="dev",
                                       profiles_yml_filepath="/opt/airflow/src/dags/models_cold/dbt_model/profiles.yml"
                                      ),
        execution_config=execution_config,
        render_config=render_config_gold,
        # operator_args=operator_args,
        #operator_args={
        #    "vars": '{"my_name": {{ params.my_name }} }',
        #},
        default_args={"retries": 2},
    )

    # Define task dependencies
    transform_bronze >> transform_silver

with DAG(
    dag_id="dbt_virtual_taskgroup_gold",
    default_args=default_args,
    description="run gold",
    schedule_interval="@daily",
    start_date=datetime(2025, 1, 28),
    catchup=False,
) as dag:

    dbt_env_vars = {
        "TRINO_USER": Variable.get("trino_user", default_var="kmikolajczyk"),
        "TRINO_PASSWD": Variable.get("trino_passwd", default_var="Begat-windward-rascal-common-chaperon"),
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
        "logical_date": "{{ ds }}",
        "year": "{{ ds[:4] }}",
        "month": "{{ ds[5:7] }}",   # Extract the month
        "day": "{{ ds[8:10] }}",    # Extract the day
        "hour": "{{ ts[11:13] }}",  # Extract the hour from timestamp
    }
    

    # TaskGroup for DBT
    transform_gold = DbtTaskGroup(
        group_id="transform_gold",
        project_config=ProjectConfig(dbt_project_path=DBT_PROJECT_PATH,
                                     env_vars=dbt_env_vars,
                                     dbt_vars=dbt_env_vars),
        profile_config = ProfileConfig(profile_name="datahub",
                                       target_name="dev",
                                       profiles_yml_filepath="/opt/airflow/src/dags/models_cold/dbt_model/profiles.yml"
                                      ),
        execution_config=execution_config,
        render_config=render_config_gold,
        # operator_args=operator_args,
        #operator_args={
        #    "vars": '{"my_name": {{ params.my_name }} }',
        #},
        default_args={"retries": 2},
    )

    # Define task dependencies
    transform_gold

