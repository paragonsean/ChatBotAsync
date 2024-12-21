# main.py

import streamlit as st
from openai_client import OpenAIClient
from helpers import (
    deep_merge_dicts,
    load_openapi_schemas,
    validate_openapi_schema,
    get_endpoints_and_explanations,
    generate_json_for_endpoint,
    cleanup_temp_directory
)
from typing import List, Optional, Dict
import json
import openai
from datetime import datetime
import os
import time

# -----------------------------
# Streamlit UI
# -----------------------------
def main():
    st.title("OpenAPI Schema Query App with Retrieval-Augmented Generation (RAG)")

    st.write("""
        **Upload your OpenAPI schema files (JSON or YAML).** The app will load, merge, validate the schema, embed the endpoints, and store them in a Vector Store using separate namespaces for each file. You can then ask questions, and the app will retrieve relevant information to generate informed responses.
    """)

    # -----------------------------
    # Initialize OpenAIClient
    # -----------------------------
    st.sidebar.header("API Keys Configuration")

    # Access API keys from Streamlit secrets
    try:
        openai_api_key = st.secrets["openai"]["api_key"]
        pinecone_api_key = st.secrets["pinecone"]["api_key"]
        pinecone_env = st.secrets["pinecone"]["environment"]
        pinecone_index = st.secrets["pinecone"]["index_name"]
    except KeyError as e:
        st.error(f"Missing API key in secrets: {e}")
        return

    # Instantiate the OpenAIClient
    client = OpenAIClient(
        api_key=openai_api_key,
        pinecone_api_key=pinecone_api_key,
        pinecone_env=pinecone_env,
        index_name=pinecone_index
    )

    # -----------------------------
    # Cleanup Temporary Directory
    # -----------------------------
    cleanup_temp_directory()

    # -----------------------------
    # File uploader to upload multiple OpenAPI schema files
    # -----------------------------
    uploaded_schema_files = st.file_uploader(
        "Upload OpenAPI Schema Files",
        type=["json", "yaml", "yml"],
        accept_multiple_files=True,
        key="schema_files"
    )

    # Display uploaded file names
    if uploaded_schema_files:
        st.write("### Uploaded Schema Files:")
        for file in uploaded_schema_files:
            st.write(f"- {file.name}")

    # -----------------------------
    # Load and Validate OpenAPI Schema
    # -----------------------------
    if uploaded_schema_files:
        openapi_schema = load_openapi_schemas(uploaded_schema_files)
    else:
        st.info("No schema files uploaded. You can upload schema files above.")

    if 'openapi_schema' in locals() and openapi_schema:
        st.success("OpenAPI schema loaded successfully!")

        # Validate the schema
        st.write("### Validating OpenAPI Schema")
        validate_openapi_schema(openapi_schema)

        # Extract endpoints
        endpoints_info = get_endpoints_and_explanations(openapi_schema)
        if endpoints_info:
            st.write("### Available API Endpoints")

            # Assign a unique namespace to each uploaded file based on its name
            namespace_mapping = {}
            for file in uploaded_schema_files:
                # Generate a namespace name from the file name
                namespace = f"namespace_{file.name.replace('.', '_')}"
                namespace_mapping[file.name] = namespace

            # Display the namespace mapping
            st.write("### Namespace Mapping")
            for file_name, namespace in namespace_mapping.items():
                st.write(f"- **{file_name}**: `{namespace}`")

            # -----------------------------
            # Manage Endpoints Section
            # -----------------------------
            st.markdown("---")
            st.header("Manage Endpoints")

            # Allow user to select which file's endpoints to manage
            selected_file = st.selectbox(
                "Select a File to Manage Endpoints",
                options=[file.name for file in uploaded_schema_files],
                key="select_file_manage"
            )

            selected_namespace = namespace_mapping[selected_file]

            # Button to add all endpoints from the selected file to Pinecone
            if st.button("Add All Endpoints from Selected File to Vector Store"):
                with st.spinner(f"Adding all endpoints from '{selected_file}' to Vector Store..."):
                    success_count = 0
                    failure_count = 0
                    for endpoint in endpoints_info:
                        path = endpoint['path']
                        method = endpoint['method']
                        summary = endpoint['summary']

                        # Generate JSON for the endpoint
                        endpoint_json = generate_json_for_endpoint(openapi_schema, path, method)
                        if not endpoint_json:
                            failure_count += 1
                            continue

                        # Generate a unique base ID for the endpoint
                        base_id = f"{method}_{path}".replace("/", "_").replace("{", "").replace("}", "")

                        # Define metadata
                        metadata = {
                            "endpoint": path,
                            "method": method,
                            "summary": summary,
                            "timestamp": datetime.now().isoformat(),
                            "file_name": selected_file
                        }

                        # Upsert embeddings with text splitting and metadata into the specific namespace
                        try:
                            client.upsert_embeddings(
                                id=base_id,
                                text=endpoint_json,
                                metadata=metadata,
                                namespace=selected_namespace,
                                chunk_size=8000,
                                batch_size=500,
                                max_workers=5
                            )
                            success_count += 1
                        except Exception as e:
                            st.error(f"Failed to upsert endpoint {method} {path}: {e}")
                            failure_count += 1

                    st.success(f"Successfully upserted {success_count} endpoints from '{selected_file}'.")
                    if failure_count > 0:
                        st.warning(f"Failed to upsert {failure_count} endpoints from '{selected_file}'.")

            # Button to add individual endpoints
            st.markdown("---")
            st.subheader("Add Individual Endpoint")

            # Allow user to select a specific endpoint from the selected file
            # Assuming endpoints_info contains all endpoints; adjust if endpoints are file-specific
            endpoints_from_selected_file = [ep for ep in endpoints_info if ep.get('file_name') == selected_file] if 'file_name' in endpoints_info[0] else endpoints_info

            if not endpoints_from_selected_file:
                st.warning("No endpoints found for the selected file.")
            else:
                # Create a list of display names for the dropdown
                endpoint_options = [f"{ep['method']} {ep['path']} - {ep['summary']}" for ep in endpoints_from_selected_file]
                selected_endpoint_display = st.selectbox("Select an Endpoint to Add", options=endpoint_options, key="select_individual_endpoint")

                # Find the selected endpoint
                selected_endpoint = next((ep for ep in endpoints_from_selected_file if f"{ep['method']} {ep['path']} - {ep['summary']}" == selected_endpoint_display), None)

                if selected_endpoint:
                    if st.button("Add Selected Endpoint to Vector Store"):
                        with st.spinner(f"Adding endpoint {selected_endpoint['method']} {selected_endpoint['path']} to Vector Store..."):
                            path = selected_endpoint['path']
                            method = selected_endpoint['method']
                            summary = selected_endpoint['summary']

                            # Generate JSON for the endpoint
                            endpoint_json = generate_json_for_endpoint(openapi_schema, path, method)
                            if not endpoint_json:
                                st.error("Failed to generate JSON for the selected endpoint.")
                            else:
                                # Generate a unique base ID for the endpoint
                                base_id = f"{method}_{path}".replace("/", "_").replace("{", "").replace("}", "")

                                # Define metadata
                                metadata = {
                                    "endpoint": path,
                                    "method": method,
                                    "summary": summary,
                                    "timestamp": datetime.now().isoformat(),
                                    "file_name": selected_file
                                }

                                # Upsert embeddings with text splitting and metadata into the specific namespace
                                try:
                                    client.upsert_embeddings(
                                        id=base_id,
                                        text=endpoint_json,
                                        metadata=metadata,
                                        namespace=selected_namespace,
                                        chunk_size=8000,
                                        batch_size=500,
                                        max_workers=5
                                    )
                                    st.success(f"Successfully upserted endpoint {method} {path} into namespace '{selected_namespace}'.")
                                except Exception as e:
                                    st.error(f"Failed to upsert endpoint {method} {path}: {e}")

    # Add a separator
        st.markdown("---")

        # -----------------------------
        # Querying the Assistant
        # -----------------------------
        st.header("Ask a Question About the OpenAPI Schema")

        # Allow user to select which namespace to query
        if uploaded_schema_files:
            namespaces = [f"namespace_{file.name.replace('.', '_')}" for file in uploaded_schema_files]
            namespaces.append("")  # For default namespace
            selected_query_namespace = st.selectbox("Select Namespace to Query", options=namespaces, index=len(namespaces)-1, key="select_query_namespace")
        else:
            selected_query_namespace = ""

        user_query = st.text_input("Enter your query:", key="user_query")
        top_k = st.slider("Number of Relevant Documents to Retrieve:", min_value=1, max_value=10, value=5)

        if st.button("Submit Query"):
            if not user_query:
                st.error("Please enter a query before submitting.")
            else:
                with st.spinner("Processing your query..."):
                    # Step 1: Query the Vector Store
                    search_results = client.query_vector_store(query=user_query, top_k=top_k, namespace=selected_query_namespace)

                    if search_results:
                        # Step 2: Compile retrieved contents
                        retrieved_contents = "\n\n---\n\n".join([result['content'] for result in search_results])

                        # Step 3: Generate a response using OpenAI's ChatCompletion with retrieved context
                        try:
                            response = openai.ChatCompletion.create(
                                model="gpt-4",  # Use "gpt-4" or another available model
                                messages=[
                                    {"role": "system",
                                     "content": "You are a helpful assistant that answers questions based on the provided OpenAPI schema information."},
                                    {"role": "user",
                                     "content": f"Based on the following information:\n\n{retrieved_contents}\n\nAnswer the question: {user_query}"}
                                ],
                                temperature=0.2  # Adjust temperature as needed
                            )
                            assistant_reply = response['choices'][0]['message']['content']
                            st.write("### Response to Your Query:")
                            st.write(assistant_reply)
                        except Exception as e:
                            st.error(f"Failed to generate response: {e}")
                    else:
                        st.error("No relevant information found in the Vector Store.")

    # -----------------------------
    # Vector Store Management Section
    # -----------------------------
        st.markdown("---")
        st.header("Vector Store Management")

        # Option to describe index statistics
        if st.button("Describe Index Statistics"):
            stats = client.describe_index_statistics()
            if stats:
                st.write("### Index Statistics")
                st.json(stats)

        st.subheader("List All Namespaces")

        if st.button("List Namespaces"):
            with st.spinner("Fetching namespaces..."):
                namespaces = client.list_namespaces()
                if namespaces:
                    st.write("### Available Namespaces:")
                    for ns in namespaces:
                        st.write(f"- `{ns}`")
                else:
                    st.warning("No namespaces found.")

        st.subheader("List IDs in a Namespace")

        # Allow user to select a namespace to list IDs
        if uploaded_schema_files:
            # Fetch namespaces from Pinecone
            namespaces = client.list_namespaces()

            st.write("### Retrieved Namespaces from Pinecone:")
            st.write(namespaces)

            if namespaces:
                selected_list_namespace = st.selectbox(
                    "Select Namespace to List IDs",
                    options=namespaces,
                    index=0,  # Default to the first namespace
                    key="select_list_namespace"
                )

                # Optional: Allow user to input a prefix to filter IDs
                prefix = st.text_input("Enter ID Prefix (optional):", key="id_prefix_list")

                # Specify the number of IDs per page
                limit = st.number_input("Number of IDs per Page:", min_value=1, max_value=1000, value=100, step=1, key="ids_per_page_list")

                # Initialize session state for pagination tokens
                if 'pagination_token' not in st.session_state:
                    st.session_state.pagination_token = None

                # Function to reset pagination
                def reset_pagination():
                    st.session_state.pagination_token = None

                # Buttons for pagination
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("Previous Page"):
                        st.warning("Previous page functionality not implemented.")
                with col2:
                    if st.button("Next Page"):
                        with st.spinner("Fetching next page of IDs..."):
                            results = client.list_ids_in_namespace_paginated(
                                namespace=selected_list_namespace,
                                prefix=prefix,
                                limit=limit,
                                pagination_token=st.session_state.pagination_token
                            )
                            if results and results["ids"]:
                                st.session_state.pagination_token = results["next_token"]
                                # Display IDs as a dropdown for selection
                                selected_vector_id = st.selectbox("Select a Vector ID from Next Page", options=results["ids"], key="select_next_vector_id")
                                st.write(f"Selected Vector ID: `{selected_vector_id}`")
                            else:
                                st.warning("No IDs found in this page.")
                with col3:
                    if st.button("Reset Pagination"):
                        reset_pagination()
                        st.success("Pagination reset.")

                # Display current page of IDs as a dropdown list
                with st.spinner("Fetching vector IDs..."):
                    if st.session_state.pagination_token:
                        results = client.list_ids_in_namespace_paginated(
                            namespace=selected_list_namespace,
                            prefix=prefix,
                            limit=limit,
                            pagination_token=st.session_state.pagination_token
                        )
                    else:
                        results = client.list_ids_in_namespace_paginated(
                            namespace=selected_list_namespace,
                            prefix=prefix,
                            limit=limit
                        )

                    if results and results["ids"]:
                        st.write("### Vector IDs:")
                        # Implement search/filter if necessary
                        search_query = st.text_input("Search Vector ID:", key="search_vector_id_list")
                        if search_query:
                            filtered_ids = [vid for vid in results["ids"] if search_query.lower() in vid.lower()]
                        else:
                            filtered_ids = results["ids"]

                        selected_vector_id = st.selectbox(
                            "Select a Vector ID",
                            options=filtered_ids,
                            key="select_vector_id_list"
                        )
                        st.write(f"Selected Vector ID: `{selected_vector_id}`")
                    else:
                        st.warning("No IDs found for the selected namespace and prefix.")
        else:
            st.warning("No namespaces found in the Pinecone index.")

    # -----------------------------
    # Vector Store Upload Section
    # -----------------------------
        st.markdown("---")
        st.header("Upload YAML Files to Vector Store")

        upload_yaml_files = st.file_uploader(
            "Upload YAML Files",
            type=["yaml", "yml"],
            accept_multiple_files=True,
            key="upload_yaml_files_pinecone"
        )

        if upload_yaml_files:
            st.write("### Uploaded Files:")
            for file in upload_yaml_files:
                st.write(f"- {file.name}")
                # Save uploaded files temporarily to disk
                os.makedirs("./temp", exist_ok=True)
                with open(f"./temp/{file.name}", "wb") as f:
                    f.write(file.getbuffer())

            if st.button("Upload Files to Vector Store"):
                with st.spinner("Uploading files and upserting into Vector Store..."):
                    success_count = 0
                    failure_count = 0
                    for file in upload_yaml_files:
                        try:
                            # Convert YAML to JSON
                            with open(f"./temp/{file.name}", "rb") as f:
                                json_content = client.convert_yaml_to_json(f)
                            if not json_content:
                                st.error(f"Failed to convert {file.name} to JSON.")
                                failure_count += 1
                                continue

                            # Generate a unique namespace for the file
                            namespace = f"namespace_{file.name.replace('.', '_')}"

                            # Define metadata (customize as per your requirements)
                            metadata = {
                                "file_name": file.name,
                                "uploaded_at": datetime.now().isoformat()
                            }

                            # Upsert embeddings with text splitting and metadata into the specific namespace
                            client.upsert_embeddings(
                                id=file.name,  # Use file name as base ID
                                text=json_content,
                                metadata=metadata,
                                namespace=namespace,
                                chunk_size=8000,
                                batch_size=500,
                                max_workers=5
                            )
                            success_count += 1
                            st.success(f"Uploaded and upserted {file.name} successfully into namespace '{namespace}'.")
                        except Exception as e:
                            st.error(f"Failed to upload and upsert {file.name}: {e}")
                            failure_count += 1

                    st.info(f"Total Successfully Uploaded Files: {success_count}")
                    if failure_count > 0:
                        st.warning(f"Total Failed Uploads: {failure_count}")

    # Add a separator
        st.markdown("---")

if __name__ == "__main__":
    main()
