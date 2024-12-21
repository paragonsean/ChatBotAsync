import requests
import openai
import streamlit as st
from typing import List, Optional, Dict
from datetime import datetime
import json

class OpenAIClient:
    """
    A client to interact with OpenAI's Files API and Vector Store API.
    """

    def __init__(self, api_key: str, vector_store_id: str, assistant_id: str):
        """
        Initializes the OpenAIClient with necessary credentials.

        Args:
            api_key (str): OpenAI API key.
            vector_store_id (str): ID of the Vector Store.
            assistant_id (str): ID of the Assistant.
        """
        self.api_key = api_key
        self.vector_store_id = vector_store_id
        self.assistant_id = assistant_id
        openai.api_key = self.api_key

    # -----------------------------
    # Custom JSON Encoder
    # -----------------------------
    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime):
                return obj.isoformat()  # Convert datetime to ISO 8601 string
            return super().default(obj)

    # -----------------------------
    # OpenAI Files API Methods
    # -----------------------------
    def upload_file_to_openai(self, file, purpose: str = 'assistants') -> Optional[Dict]:
        """
        Uploads a file to OpenAI's Files API.

        Args:
            file: The uploaded file from Streamlit.
            purpose (str): The purpose of the file (e.g., 'assistants').

        Returns:
            dict: A dictionary containing file information if successful, None otherwise.
        """
        url = "https://api.openai.com/v1/files"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        files = {
            'file': (file.name, file, 'application/octet-stream')
        }
        data = {
            'purpose': purpose
        }

        try:
            response = requests.post(url, headers=headers, files=files, data=data)
            response.raise_for_status()
            st.success(f"Uploaded {file.name} successfully.")
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            st.error(f"HTTP error occurred while uploading {file.name}: {http_err} - {response.text}")
        except Exception as err:
            st.error(f"An error occurred while uploading {file.name}: {err}")
        return None

    def list_openai_files(self) -> Optional[Dict]:
        """
        Lists all files uploaded to OpenAI's Files API.

        Returns:
            dict: A dictionary containing the list of files if successful, None otherwise.
        """
        url = "https://api.openai.com/v1/files"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            st.error(f"HTTP error occurred while listing files: {http_err} - {response.text}")
        except Exception as err:
            st.error(f"An error occurred while listing files: {err}")
        return None

    def delete_openai_file(self, file_id: str) -> Optional[Dict]:
        """
        Deletes a file from OpenAI's Files API.

        Args:
            file_id (str): The ID of the file to delete.

        Returns:
            dict: A dictionary confirming deletion if successful, None otherwise.
        """
        url = f"https://api.openai.com/v1/files/{file_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            response = requests.delete(url, headers=headers)
            response.raise_for_status()
            st.success(f"Deleted file with ID: {file_id} successfully.")
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            st.error(f"HTTP error occurred while deleting file {file_id}: {http_err} - {response.text}")
        except Exception as err:
            st.error(f"An error occurred while deleting file {file_id}: {err}")
        return None

    # -----------------------------
    # Vector Store API Methods
    # -----------------------------
    def list_vector_store_files(self, limit: int = 20, order: str = "desc",
                                after: Optional[str] = None, before: Optional[str] = None,
                                filter_status: Optional[str] = None) -> Optional[Dict]:
        """
        Lists files in the specified vector store.

        Args:
            limit (int): Number of files to retrieve.
            order (str): Sort order ('asc' or 'desc').
            after (str, optional): Cursor for pagination.
            before (str, optional): Cursor for pagination.
            filter_status (str, optional): Filter files by status.

        Returns:
            dict: A dictionary containing the list of vector store files if successful, None otherwise.
        """
        url = f"https://api.openai.com/v1/vector_stores/{self.vector_store_id}/files"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "OpenAI-Beta": "assistants=v2"
        }
        params = {
            "limit": limit,
            "order": order
        }
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        if filter_status:
            params["filter"] = filter_status

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            st.error(f"HTTP error occurred: {http_err} - {response.text}")
        except Exception as err:
            st.error(f"An error occurred: {err}")
        return None

    def retrieve_vector_store_file(self, file_id: str) -> Optional[Dict]:
        """
        Retrieves details of a specific vector store file.

        Args:
            file_id (str): The ID of the file to retrieve.

        Returns:
            dict: A dictionary containing file details if successful, None otherwise.
        """
        url = f"https://api.openai.com/v1/vector_stores/{self.vector_store_id}/files/{file_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "OpenAI-Beta": "assistants=v2"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            st.error(f"HTTP error occurred: {http_err} - {response.text}")
        except Exception as err:
            st.error(f"An error occurred: {err}")
        return None

    def delete_vector_store_file(self, file_id: str) -> Optional[Dict]:
        """
        Deletes a file from the specified vector store.

        Args:
            file_id (str): The ID of the file to delete.

        Returns:
            dict: A dictionary confirming deletion if successful, None otherwise.
        """
        url = f"https://api.openai.com/v1/vector_stores/{self.vector_store_id}/files/{file_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "OpenAI-Beta": "assistants=v2"
        }

        try:
            response = requests.delete(url, headers=headers)
            response.raise_for_status()
            st.success(f"Deleted vector store file with ID: {file_id} successfully.")
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            st.error(f"HTTP error occurred while deleting vector store file {file_id}: {http_err} - {response.text}")
        except Exception as err:
            st.error(f"An error occurred while deleting vector store file {file_id}: {err}")
        return None

    def create_vector_store_file_batch(self, file_ids: List[str],
                                       chunking_strategy: Optional[Dict] = None) -> Optional[Dict]:
        """
        Creates a vector store file batch to add multiple files to the vector store.

        Args:
            file_ids (List[str]): A list of file IDs to add.
            chunking_strategy (Dict, optional): Optional chunking strategy.

        Returns:
            dict: A dictionary containing batch information if successful, None otherwise.
        """
        url = f"https://api.openai.com/v1/vector_stores/{self.vector_store_id}/file_batches"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "OpenAI-Beta": "assistants=v2"
        }
        payload = {
            "file_ids": file_ids
        }
        if chunking_strategy:
            payload["chunking_strategy"] = chunking_strategy

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            st.success("Vector store file batch created successfully!")
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            st.error(f"HTTP error occurred while creating file batch: {http_err} - {response.text}")
        except Exception as err:
            st.error(f"An error occurred while creating file batch: {err}")
        return None

    def retrieve_vector_store_file_batch(self, batch_id: str) -> Optional[Dict]:
        """
        Retrieves details of a specific vector store file batch.

        Args:
            batch_id (str): The ID of the batch to retrieve.

        Returns:
            dict: A dictionary containing batch details if successful, None otherwise.
        """
        url = f"https://api.openai.com/v1/vector_stores/{self.vector_store_id}/file_batches/{batch_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "OpenAI-Beta": "assistants=v2"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            st.error(f"HTTP error occurred while retrieving file batch: {http_err} - {response.text}")
        except Exception as err:
            st.error(f"An error occurred while retrieving file batch: {err}")
        return None
