import os
import streamlit as st
import openai
import json
import yaml
import jsonref
from jsonschema import validate, ValidationError
from openapi_schema_validator import OAS30Validator
from datetime import datetime

# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()  # Convert datetime to ISO 8601 string
        return super(DateTimeEncoder, self).default(obj)

# Function to handle querying the OpenAPI schema using LLM
def query_openapi_schema(openapi_schema, query):
    try:
        # Use OpenAI API to process the query
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Replace with your preferred model
            messages=[
                {"role": "system",
                 "content": f"You are an assistant with knowledge of OpenAPI schema. The schema: {json.dumps(openapi_schema, cls=DateTimeEncoder)}"},
                {"role": "user", "content": query}
            ]
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        st.error(f"Failed to query the schema: {e}")
        return None


# Function to load the OpenAPI schema from a file or load the default one and resolve $refs
def load_openapi_schema(file=None):
    try:
        if file is not None:  # If a file is uploaded by the user
            if file.name.endswith('.json'):
                schema = json.load(file)
            elif file.name.endswith('.yaml') or file.name.endswith('.yml'):
                schema = yaml.safe_load(file)
            else:
                st.error("Unsupported file type. Please upload a JSON or YAML file.")
                return None
        else:
            # Load default openapi.yaml if no file is uploaded
            default_file_path = "openapi.yaml"
            if os.path.exists(default_file_path):
                with open(default_file_path, 'r') as default_file:
                    schema = yaml.safe_load(default_file)
            else:
                st.error(f"Default OpenAPI schema file '{default_file_path}' not found.")
                return None

        # Resolve $ref references using jsonref
        resolved_schema = jsonref.JsonRef.replace_refs(schema)
        return resolved_schema

    except Exception as e:
        st.error(f"Failed to load schema: {e}")
        return None


# Function to validate OpenAPI schema
def validate_openapi_schema(openapi_schema):
    try:
        validator = OAS30Validator(openapi_schema)
        validator.validate(openapi_schema)
        st.success("OpenAPI schema is valid!")
    except ValidationError as e:
        st.error(f"OpenAPI schema validation failed: {e}")
    except Exception as e:
        st.error(f"Failed to validate schema: {e}")


# Function to extract and explain endpoints
def get_endpoints_and_explanations(openapi_schema):
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


# Function to generate JSON for a specific endpoint
def generate_json_for_endpoint(openapi_schema, selected_path, selected_method):
    try:
        path_methods = openapi_schema["paths"].get(selected_path, {})
        method_details = path_methods.get(selected_method.lower(), {})
        if method_details:
            # Generate a clean JSON output for the specific method and path
            return json.dumps({selected_method.upper(): {selected_path: method_details}}, indent=4)
        else:
            st.error("No details found for the selected endpoint.")
            return None
    except Exception as e:
        st.error(f"Failed to generate JSON for the selected endpoint: {e}")
        return None


# Streamlit UI
st.title("OpenAPI Schema Query App")

st.write("""
    Upload your OpenAPI schema (JSON or YAML), or the default schema will be loaded automatically.
    Choose whether to get information about the API or retrieve specific data.
    You can also extract and explain the endpoints or generate a JSON summary.
""")

# File uploader to upload OpenAPI schema
uploaded_file = st.file_uploader("Upload OpenAPI Schema", type=["json", "yaml", "yml"])

# OpenAI API key setup from Streamlit secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Load the OpenAPI schema: either from the uploaded file or the default one
openapi_schema = load_openapi_schema(uploaded_file)

if openapi_schema:
    st.success("OpenAPI schema loaded successfully!")

    # Validate the schema
    st.write("### Validating OpenAPI Schema")
    validate_openapi_schema(openapi_schema)

    # Button to extract and explain endpoints
    endpoints_info = get_endpoints_and_explanations(openapi_schema)
    if endpoints_info:
        st.write("### Available API Endpoints")

        # Allow user to select a path and method from the available endpoints
        paths = list({endpoint['path'] for endpoint in endpoints_info})
        selected_path = st.selectbox("Select an API path", paths)

        # Get available methods for the selected path
        methods = [endpoint['method'] for endpoint in endpoints_info if endpoint['path'] == selected_path]
        selected_method = st.selectbox("Select an HTTP method", methods)

        # Button to generate JSON for the selected endpoint
        if st.button("Generate JSON for Selected Endpoint"):
            endpoint_json = generate_json_for_endpoint(openapi_schema, selected_path, selected_method)
            if endpoint_json:
                st.write("### Generated JSON for Selected Endpoint")
                st.json(endpoint_json)

    # Section for querying the schema
    st.write("### Ask a Question About the OpenAPI Schema")

    # Text input for the user's query
    user_query = st.text_input("Enter your query about the OpenAPI schema:")

    # Button to process the query using OpenAI
    if st.button("Submit Query"):
        if user_query:
            query_response = query_openapi_schema(openapi_schema, user_query)
            if query_response:
                st.write("### Response to Your Query")
                st.write(query_response)
        else:
            st.error("Please enter a query before submitting.")
