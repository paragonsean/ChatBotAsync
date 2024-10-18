import os

import streamlit as st
import openai
import json
import yaml
from jsonschema import validate

from dotenv import load_dotenv
load_dotenv()
# Function to load the OpenAPI schema
def load_openapi_schema(file):
    try:
        if file.name.endswith('.json'):
            return json.load(file)
        elif file.name.endswith('.yaml') or file.name.endswith('.yml'):
            return yaml.safe_load(file)
        else:
            st.error("Unsupported file type. Please upload a JSON or YAML file.")
            return None
    except Exception as e:
        st.error(f"Failed to load schema: {e}")
        return None


# Function to handle querying the OpenAPI schema using LLM
def query_openapi_schema(openapi_schema, query):
    try:
        # Use OpenAI API to process the query
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Replace with your preferred model
            messages=[
                {"role": "system",
                 "content": f"You are an assistant with knowledge of OpenAPI schema. The schema: {json.dumps(openapi_schema)}"},
                {"role": "user", "content": query}
            ]
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        st.error(f"Failed to query the schema: {e}")
        return None


# Streamlit UI
st.title("OpenAPI Schema Query App")

st.write("""
    Upload your OpenAPI schema (JSON or YAML), and choose whether to get information about the API 
    or retrieve specific data. The application will query the schema using an LLM.
""")

# File uploader to upload OpenAPI schema
uploaded_file = st.file_uploader("Upload OpenAPI Schema", type=["json", "yaml", "yml"])

# Once the file is uploaded
if uploaded_file is not None:
    openapi_schema = load_openapi_schema(uploaded_file)

    if openapi_schema:
        st.success("OpenAPI schema loaded successfully!")

        # Ask the user if they want to get information or retrieve data
        action = st.radio("What would you like to do?", ("Get Information", "Retrieve Data"))

        if action == "Get Information":
            # Input for the query to get information
            query = st.text_input("Enter your question about the API:")

            if query:
                response = query_openapi_schema(openapi_schema, query)
                if response:
                    st.write("### LLM Response")
                    st.write(response)

        elif action == "Retrieve Data":
            # Input for the data retrieval query (for example, a GET request)
            query = st.text_input("What data would you like to retrieve? (e.g., '/users')")

            if query:
                response = query_openapi_schema(openapi_schema, f"How do I retrieve data from {query}?")
                if response:
                    st.write("### LLM Response")
                    st.write(response)
openai.api_key = os.getenv("OPENAI_API_KEY")
# OpenAI API key input (you can set it in Streamlit secrets for security)
