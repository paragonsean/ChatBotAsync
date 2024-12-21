# openai_client.py

import openai
import streamlit as st
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import yaml
import jsonref
from pinecone import Pinecone, ServerlessSpec
import concurrent.futures
from tenacity import retry, stop_after_attempt, wait_exponential

def split_text_by_tokens(text: str, max_tokens: int = 8000) -> List[str]:
    """
    Splits the input text into smaller chunks not exceeding max_tokens tokens.
    """
    encoding = tiktoken.get_encoding("cl100k_base")  # Adjust based on your model's encoding
    tokens = encoding.encode(text)

    chunks = []
    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i + max_tokens]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)

    return chunks

class OpenAIClient:
    """
    A client to interact with OpenAI's API and Pinecone Vector Store for Retrieval-Augmented Generation (RAG).
    """

    def __init__(self, api_key: str, pinecone_api_key: str, pinecone_env: str, index_name: str):
        """
        Initializes the OpenAIClient with necessary credentials.
        """
        self.api_key = api_key
        openai.api_key = self.api_key

        self.pinecone_api_key = pinecone_api_key
        self.pinecone_env = pinecone_env
        self.index_name = index_name

        # Initialize Pinecone
        try:
            self.pc = Pinecone(api_key=self.pinecone_api_key)
            self.spec = ServerlessSpec(cloud='aws', region='us-east-1')  # Update as needed
            if self.index_name not in self.pc.list_indexes().names():
                self.pc.create_index(
                    name=self.index_name,
                    dimension=1536,  # Dimensionality for text-embedding-ada-002
                    metric='cosine',
                    spec=self.spec
                )
                st.success(f"Pinecone index '{self.index_name}' created.")
            else:
                st.info(f"Pinecone index '{self.index_name}' already exists.")

            self.index = self.pc.Index(self.index_name)
        except Exception as e:
            st.error(f"Failed to initialize Pinecone: {e}")

    # -----------------------------
    # Helper Methods
    # -----------------------------
    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return super().default(obj)

    def convert_yaml_to_json(self, file) -> Optional[str]:
        """
        Converts a YAML file to a JSON-formatted string.
        """
        try:
            yaml_content = yaml.safe_load(file)
            json_content = json.dumps(yaml_content, indent=4)
            return json_content
        except Exception as e:
            st.error(f"Failed to convert YAML to JSON: {e}")
            return None

    # -----------------------------
    # Vector Store Methods
    # -----------------------------
    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10))
    def upsert_batch(self, batch: List[tuple], namespace: str):
        """
        Upserts a batch of vectors into Pinecone within a specified namespace.
        """
        self.index.upsert(vectors=batch, namespace=namespace)
        st.info(f"Upserted batch containing {len(batch)} vectors into namespace '{namespace}'.")

    def upsert_embeddings(self, id: str, text: str, metadata: Dict[str, Any] = {}, namespace: str = "", chunk_size: int = 8000, batch_size: int = 500, max_workers: int = 5):
        """
        Generates embeddings for the given text (split into chunks) and upserts them into Pinecone within a specified namespace using parallel processing.
        """
        try:
            # Split the text into smaller chunks based on tokens
            chunks = split_text_by_tokens(text, max_tokens=chunk_size)

            vectors = []
            for idx, chunk in enumerate(chunks):
                # Generate a unique ID for each chunk
                chunk_id = f"{id}_chunk_{idx}"

                # Generate embedding for the chunk
                embedding_response = openai.Embedding.create(
                    input=chunk,
                    model="text-embedding-ada-002"
                )
                embedding = embedding_response['data'][0]['embedding']

                # Prepare the vector with metadata
                vector_metadata = metadata.copy()
                vector_metadata["chunk_id"] = chunk_id  # Example of adding more metadata

                vectors.append((chunk_id, embedding, {"content": chunk, **vector_metadata}))

            # Define a helper function for upserting a batch
            def upsert_batch_wrapper(batch):
                self.upsert_batch(batch, namespace)

            # Batch upsert with parallel processing
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(upsert_batch_wrapper, vectors[i:i + batch_size])
                    for i in range(0, len(vectors), batch_size)
                ]
                # Wait for all upserts to complete
                concurrent.futures.wait(futures)

            st.success(f"Successfully upserted all {len(vectors)} vectors with base ID: {id} into namespace '{namespace}'.")
        except Exception as e:
            st.error(f"Failed to upsert embeddings: {e}")

    def query_vector_store(self, query: str, top_k: int = 5, namespace: str = "") -> Optional[List[Dict]]:
        """
        Queries the Pinecone Vector Store within a specified namespace using the provided query string.
        """
        try:
            embedding_response = openai.Embedding.create(
                input=query,
                model="text-embedding-ada-002"
            )
            query_embedding = embedding_response['data'][0]['embedding']

            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                namespace=namespace
            )

            formatted_results = []
            for match in results.matches:
                formatted_results.append({
                    "id": match.id,
                    "score": match.score,
                    "content": match.metadata.get("content", "No content available")
                })

            return formatted_results

        except Exception as e:
            st.error(f"An error occurred during Vector Store query: {e}")
            return None

    def delete_vector(self, id: str, namespace: str = ""):
        """
        Deletes a vector from Pinecone by its ID within a specified namespace.
        """
        try:
            self.index.delete(ids=[id], namespace=namespace)
            st.success(f"Deleted vector with ID: {id} from namespace '{namespace}' successfully.")
        except Exception as e:
            st.error(f"Failed to delete vector: {e}")

    def describe_index_statistics(self) -> Optional[Dict]:
        """
        Retrieves statistics for the index, including per-namespace statistics.
        """
        try:
            stats = self.index.describe_index_stats()
            return stats
        except Exception as e:
            st.error(f"Failed to retrieve index statistics: {e}")
            return None

    def list_namespaces(self) -> Optional[List[str]]:
        """
        Lists all namespaces in the Pinecone index.
        """
        try:
            stats = self.describe_index_statistics()
            if stats and 'namespaces' in stats:
                namespaces = list(stats['namespaces'].keys())
                return namespaces
            else:
                st.warning("No namespaces found.")
                return []
        except Exception as e:
            st.error(f"Failed to list namespaces: {e}")
            return None

    def list_ids_in_namespace(self, namespace: str = "", prefix: str = "", limit: int = 100) -> List[str]:
        """
        Lists all vector IDs in a specified namespace with optional prefix and limit.
        Handles pagination automatically.
        """
        try:
            ids = []
            for batch in self.index.list(namespace=namespace, prefix=prefix, limit=limit):
                ids.extend(batch)
            return ids
        except Exception as e:
            st.error(f"Failed to list IDs in namespace '{namespace}': {e}")
            return []

    def list_ids_in_namespace_paginated(self, namespace: str = "", prefix: str = "", limit: int = 100) -> Optional[Dict]:
        """
        Lists vector IDs in a specified namespace with pagination.
        Returns a dictionary with IDs and the next pagination token.
        """
        try:
            response = self.index.list_paginated(
                prefix=prefix,
                limit=limit,
                namespace=namespace
            )
            ids = [v.id for v in response.vectors]
            next_token = response.pagination.next if response.pagination else None
            return {
                "ids": ids,
                "next_token": next_token
            }
        except Exception as e:
            st.error(f"Failed to list IDs with pagination in namespace '{namespace}': {e}")
            return None
