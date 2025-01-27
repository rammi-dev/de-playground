from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from cosmos import DbtDag, DbtTaskGroup, ExecutionMode, InvocationMode, ProjectConfig, ExecutionConfig, ProfileConfig, RenderConfig
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


# Define the project configuration
project_config = ProjectConfig(
    project_name="my_dbt_project",  # Name of your dbt project
    dbt_project_path="/opt/airflow/src/dags/models_cold/dbt_model/",  # Path to your dbt project directory
)

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
    "PATH":"/opt/airflow/src/dbt-env/bin"
}

render_config = RenderConfig(
    dbt_executable_path="DBT_EXECUTABLE_PATH", 
    env_vars={
        "TRINO_USER": "my_user",
        "TRINO_PASSWD": "my_password",
        "TRINO_HOST": "trino.example.com",
        "TRINO_PORT": "443",
        "USER_SCHEMA": "my_schema",
    },
)

execution_config=ExecutionConfig(
        # execution_mode=ExecutionMode.VIRTUALENV,
        # virtualenv_dir=Path(DBT_VENV_PATH),
        # execution_mode=ExecutionMode.VIRTUALENV,
        # invocation_mode=InvocationMode.SUBPROCESS,
        dbt_executable_path=Path(DBT_EXECUTABLE_PATH)
            # Without setting virtualenv_dir="/some/path/persistent-venv",
            # Cosmos creates a new Python virtualenv for each dbt task being executed
        )
operator_args={
            "py_system_site_packages": True,
            "py_requirements": ["dbt-core","dbt-trino"],
            # "install_deps": True,
            # "emit_datasets": False, 
              # Example of how to not set inlets and outlets
            # --------------------------------------------------------------------------
            # For the sake of avoiding additional latency observed while uploading files for each of the tasks, the
            # below callback functions to be executed are commented, but you can uncomment them if you'd like to
            # enable callback execution.
            # Callback function to upload files using Airflow Object storage and Cosmos remote_target_path setting on
            # Airflow 2.8 and above
            # "callback": upload_to_cloud_storage,
            # --------------------------------------------------------------------------
            # Callback function if you'd like to upload files from the target directory to remote store e.g. AWS S3 that
            # works with Airflow < 2.8 too
            # "callback": upload_to_aws_s3,
            # "callback_args": {"aws_conn_id": "aws_s3_conn", "bucket_name": "cosmos-artifacts-upload"}
            # --------------------------------------------------------------------------
        }

# DBT environment variables


# Custom Trino Profile Mapping
class CustomTrinoProfileMapping(TrinoBaseProfileMapping):
    def __init__(self, conn_id, **kwargs):
        super().__init__(conn_id, **kwargs)
    @property
    def profile(self):
        return {
            "target": "dev",
            "outputs": {
                "dev": {
                    "type": "trino",
                    "method": "ldap",
                    "user": dbt_env_vars["TRINO_USER"],
                    "password": dbt_env_vars["TRINO_PASSWD"],
                    "database": "iceberg",
                    "schema": dbt_env_vars["USER_SCHEMA"],
                    "host": dbt_env_vars["TRINO_HOST"],
                    "port": int(dbt_env_vars["TRINO_PORT"]),
                    "threads": 1,
                }
            }
        }


profile_config = ProfileConfig(
    profile_name="datahub",
    target_name="dev",
    profile_mapping=CustomTrinoProfileMapping(conn_id="TRINNO_CONNECT")
)

# Default arguments for the DAG
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
}


# Define the DAG
dbt_dag = DbtDag (
    dag_id="dbt_dag_run1",
    project_config=ProjectConfig(dbt_project_path=DBT_PROJECT_PATH,
                                 env_vars=dbt_env_vars),
    profile_config = ProfileConfig(profile_name="datahub",
                                    target_name="dev",
                                    profiles_yml_filepath="/opt/airflow/src/dags/models_cold/dbt_model/profiles.yml"
                                    ),
    execution_config=execution_config,
    start_date=datetime(2025, 1, 27),
    schedule_interval="@daily",
    catchup=False,
    # task_args={
    #    # Pass dynamic `--target-path`
    #    "extra_args": [
    #        "--target-path",
    #        f"{DBT_TARGET_PATH}/{{{{ dag_id }}}}_{{{{ logical_date.strftime('%Y%m%d') }}}}_{{{{ ts_nodash }}}}"
    #    ]
    # },
)
