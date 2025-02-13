import os
import json
import dlt
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import pyarrow.parquet as pq
import pandas as pd

# Define Beam options
beam_options = PipelineOptions()

# Define input and output folders
input_folder = "json_data"
output_folder = "output_parquet"
schema_folder = "schema_json"
os.makedirs(output_folder, exist_ok=True)
os.makedirs(schema_folder, exist_ok=True)

# Function to list all JSON files in the folder
def list_json_files(folder):
    return [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".json")]

# Function to extract JSON data using `dlt`
def extract_json_with_dlt(file_path):
    pipeline = dlt.pipeline(
        pipeline_name=f"pipeline_{os.path.basename(file_path)}",
        destination="filesystem",  # Not used, streaming data instead
        dataset_name="in_memory"
    )

    @dlt.resource(name=os.path.basename(file_path))
    def fetch_data():
        with open(file_path, "r") as f:
            json_data = json.load(f)
            for row in json_data:
                yield row

    extracted_data = list(pipeline.run(fetch_data, as_result=True))
    return extracted_data  # Returns a list of dicts

# Function to infer schema and serialize it to JSON
def infer_and_save_schema(data, file_path):
    if not data:
        return None

    df = pd.DataFrame(data)

    # Infer schema
    schema = {col: str(df[col].dtype) for col in df.columns}

    # Save schema to JSON
    schema_path = os.path.join(schema_folder, os.path.basename(file_path).replace(".json", "_schema.json"))
    with open(schema_path, "w") as schema_file:
        json.dump(schema, schema_file, indent=4)

    print(f"✅ Schema saved: {schema_path}")
    return schema

# Function to transform and write data to Parquet
def process_and_write_to_parquet(data, file_path):
    if not data:
        return

    # Convert to Pandas DataFrame
    df = pd.DataFrame(data)

    # Apply transformations (e.g., filter values > 200 if exists)
    if "value" in df.columns:
        df = df[df["value"] > 200]

    # Define output Parquet path
    output_path = os.path.join(output_folder, os.path.basename(file_path).replace(".json", ".parquet"))

    # Write to Parquet
    pq.write_table(pq.Table.from_pandas(df), output_path)

    print(f"✅ Data processed and saved: {output_path}")

# Apache Beam pipeline to process JSON files and infer schema
with beam.Pipeline(options=beam_options) as pipeline:
    (
        pipeline
        | "List JSON Files" >> beam.Create(list_json_files(input_folder))
        | "Extract with DLT" >> beam.Map(lambda file: (file, extract_json_with_dlt(file)))
        | "Infer Schema" >> beam.MapTuple(lambda file, data: (file, data, infer_and_save_schema(data, file)))
        | "Process & Save to Parquet" >> beam.MapTuple(lambda file, data, schema: process_and_write_to_parquet(data, file))
    )

print("✅ All JSON files processed with schemas and saved to Parquet!")

