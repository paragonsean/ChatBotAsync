# helpers.py

import os
import shutil
import streamlit as st
import json
import yaml
import jsonref
from openapi_schema_validator import OAS30Validator
from jsonschema import ValidationError
from typing import List, Optional, Dict
from openai_client import OpenAIClient  # Import OpenAIClient to access DateTimeEncoder

def deep_merge_dicts(a: dict, b: dict) -> dict:
    """
    Recursively merges two dictionaries.
    """
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                a[key] = deep_merge_dicts(a[key], b[key])
            elif isinstance(a[key], list) and isinstance(b[key], list):
                a[key].extend(b[key])
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a

def load_openapi_schemas(files: List[st.runtime.uploaded_file_manager.UploadedFile]) -> Optional[dict]:
    """
    Loads and merges multiple OpenAPI schemas from uploaded files.
    """
    try:
        merged_schema = {}
        for file in files:
            if file.name.endswith('.json'):
                schema_part = json.load(file)
            elif file.name.endswith('.yaml') or file.name.endswith('.yml'):
                schema_part = yaml.safe_load(file)
            else:
                st.warning(f"Unsupported file type: {file.name}. Skipping.")
                continue

            # Merge the schema parts
            merged_schema = deep_merge_dicts(merged_schema, schema_part)

        if not merged_schema:
            st.error("No valid schema files were uploaded.")
            return None

        # Resolve $ref references using jsonref
        resolved_schema = jsonref.JsonRef.replace_refs(merged_schema)
        return resolved_schema

    except Exception as e:
        st.error(f"Failed to load and merge schemas: {e}")
        return None

def validate_openapi_schema(openapi_schema: dict):
    """
    Validates the OpenAPI schema.
    """
    try:
        validator = OAS30Validator(openapi_schema)
        validator.validate(openapi_schema)
        st.success("OpenAPI schema is valid!")
    except ValidationError as e:
        st.error(f"OpenAPI schema validation failed: {e}")
    except Exception as e:
        st.error(f"Failed to validate schema: {e}")

def get_endpoints_and_explanations(openapi_schema: dict) -> Optional[List[Dict]]:
    """
    Extracts endpoints and their summaries from the OpenAPI schema.
    """
    try:
        # Ensure that 'paths' is a dictionary
        if isinstance(openapi_schema, dict) and 'paths' in openapi_schema:
            paths = openapi_schema['paths']
        else:
            st.error("Invalid OpenAPI schema: 'paths' not found or incorrect format.")
            return None

        endpoints_info = []

        for path, methods in paths.items():
            if isinstance(methods, dict):  # Ensure that methods are in dictionary format
                for method, details in methods.items():
                    if isinstance(details, dict):  # Ensure details are also in dictionary format
                        summary = details.get("summary", "No summary available")
                        endpoints_info.append({
                            "path": path,
                            "method": method.upper(),
                            "summary": summary
                        })
                    else:
                        st.warning(f"Skipping invalid method details for {method} {path}")
            else:
                st.warning(f"Skipping invalid method structure for {path}")

        return endpoints_info
    except Exception as e:
        st.error(f"Failed to extract endpoints: {e}")
        return None

def generate_json_for_endpoint(openapi_schema: dict, selected_path: str, selected_method: str) -> Optional[str]:
    """
    Generates JSON representation for a specific endpoint.
    """
    try:
        # Extract the relevant part of the schema for the selected path and method
        path_methods = openapi_schema["paths"].get(selected_path, {})
        method_details = path_methods.get(selected_method.lower(), {})

        if method_details:
            # Serialize only the selected method and path into JSON format
            endpoint_json = json.dumps(
                {selected_method.upper(): {selected_path: method_details}},
                cls=OpenAIClient.DateTimeEncoder,
                indent=4
            )
            return endpoint_json
        else:
            st.error("No details found for the selected endpoint.")
            return None
    except Exception as e:
        st.error(f"Failed to generate JSON for the selected endpoint: {e}")
        return None

def cleanup_temp_directory():
    """
    Cleans up the temporary directory used for storing uploaded files.
    """
    try:
        if os.path.exists("./temp"):
            shutil.rmtree("./temp")
            os.makedirs("./temp")
        else:
            os.makedirs("./temp")
    except Exception as e:
        st.error(f"Failed to clean up temporary directory: {e}")
