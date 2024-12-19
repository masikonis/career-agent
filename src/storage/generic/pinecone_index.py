import asyncio
from typing import Any, Dict, List, Optional

import pinecone
from langchain_openai import OpenAIEmbeddings

from src.config import config
from src.utils.logger import get_logger

from ..base.exceptions import StorageError
from ..base.types import EntityID
from .interfaces import GenericSearchIndex
from .types import T


class PineconeSearchIndex(GenericSearchIndex[T]):
    """Generic Pinecone search index implementation"""

    def __init__(self, embeddings: OpenAIEmbeddings, is_test: bool = False):
        """Initialize Pinecone search index"""
        self.logger = get_logger(self.__class__.__name__.lower())
        self.embeddings = embeddings

        # Initialize Pinecone
        pinecone.init(
            api_key=config["PINECONE_API_KEY"], environment=config["PINECONE_ENV"]
        )

        index_name = config["PINECONE_INDEX_NAME"]
        self.namespace = "test" if is_test else "production"

        # Check if index exists, if not create it
        if index_name not in pinecone.list_indexes():
            self.logger.info(f"Creating new index: {index_name}")
            pinecone.create_index(
                name=index_name,
                dimension=1536,  # OpenAI embedding dimension
                metric="cosine",
            )

        # Get index
        self.pinecone_index = pinecone.Index(index_name)
        self.logger.info(f"Connected to existing index: {index_name}")

        # Initialize namespace if needed
        try:
            stats = self.pinecone_index.describe_index_stats()
            if self.namespace not in stats.get("namespaces", {}):
                self.logger.info(f"Initializing namespace: {self.namespace}")
                # Create a dummy vector to initialize namespace
                dummy_id = "init_" + self.namespace
                dummy_vector = [0.0] * 1536
                self.pinecone_index.upsert(
                    vectors=[(dummy_id, dummy_vector, {})], namespace=self.namespace
                )
                # Delete the dummy vector
                self.pinecone_index.delete(ids=[dummy_id], namespace=self.namespace)
        except Exception as e:
            self.logger.error(f"Failed to initialize namespace: {e}")
            raise StorageError(f"Failed to initialize Pinecone namespace: {e}")

        self.logger.info(
            f"Connected to Pinecone index: {index_name} namespace: {self.namespace}"
        )

    async def index(self, entity_id: EntityID, entity: T) -> None:
        """Index a document in Pinecone"""
        try:
            # Generate embedding for the document
            text_to_embed = f"{entity.title} {entity.content}"
            self.logger.info(
                f"Generating embedding for document: {text_to_embed[:100]}..."
            )
            embedding = await self.embeddings.aembed_query(text_to_embed)

            # Convert embedding to list if it's not already
            if not isinstance(embedding, list):
                embedding = embedding.tolist()

            # Prepare metadata
            metadata = {
                "title": entity.title,
                "content": entity.content[:1000],
                "url": entity.url,
                "source": entity.source,
            }

            # Upsert to Pinecone
            self.logger.info(
                f"Upserting document {entity_id} to Pinecone namespace: {self.namespace}"
            )
            self.pinecone_index.upsert(
                vectors=[
                    (str(entity_id), embedding, metadata)
                ],  # Changed to tuple format
                namespace=self.namespace,
            )

            # Verify the document was indexed with retries
            max_retries = 3
            for i in range(max_retries):
                fetch_response = self.pinecone_index.fetch(
                    ids=[str(entity_id)], namespace=self.namespace
                )
                if str(entity_id) in fetch_response.vectors:
                    self.logger.info(f"Successfully indexed document {entity_id}")
                    return
                if i < max_retries - 1:
                    self.logger.warning(
                        f"Vector not found, retrying... (attempt {i+1}/{max_retries})"
                    )
                    await asyncio.sleep(1)  # Wait before retry

            raise StorageError(
                f"Vector {entity_id} not found after {max_retries} retries"
            )

        except Exception as e:
            self.logger.error(f"Failed to index document: {str(e)}")
            self.logger.error(f"Document ID: {entity_id}, Title: {entity.title}")
            raise StorageError(f"Document indexing failed: {str(e)}")

    async def delete_from_index(self, doc_id: EntityID) -> None:
        """Delete a document from the index"""
        try:
            self.pinecone_index.delete(ids=[str(doc_id)], namespace=self.namespace)
        except Exception as e:
            self.logger.error(f"Failed to delete document {doc_id}: {str(e)}")
            raise StorageError(f"Document deletion failed: {str(e)}")

    async def search(
        self, query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 10
    ) -> List[EntityID]:
        """Search for documents by text query"""
        try:
            # First, let's see what's in the index
            stats = self.pinecone_index.describe_index_stats()
            self.logger.info(f"Index stats: {stats}")

            # Generate query embedding
            self.logger.info(f"Generating embedding for query: {query}")
            query_embedding = await self.embeddings.aembed_query(query)

            # Search in Pinecone with minimal parameters
            self.logger.info(f"Searching Pinecone with namespace: {self.namespace}")
            results = self.pinecone_index.query(
                namespace=self.namespace,
                vector=query_embedding,
                top_k=limit,
                include_metadata=True,
                score_threshold=0.0,  # Accept all matches
            )

            # Log results in detail
            self.logger.info(f"Pinecone returned {len(results.matches)} matches")
            for match in results.matches:
                self.logger.info(f"Match ID: {match.id}, Score: {match.score}")
                self.logger.info(f"Match metadata: {match.metadata}")

            # Return just the IDs
            return [match.id for match in results.matches]

        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            self.logger.error(
                f"Query: {query}, Namespace: {self.namespace}, Filters: {filters}"
            )
            raise StorageError(f"Search failed: {str(e)}")

    async def find_similar(self, query: str, limit: int = 5) -> List[T]:
        """Search for similar documents with full metadata"""
        try:
            # Generate query embedding
            query_embedding = await self.embeddings.aembed_query(query)

            # Search in Pinecone
            results = self.pinecone_index.query(
                namespace=self.namespace,
                vector=query_embedding,
                top_k=limit,
                include_metadata=True,
            )

            # Convert results to documents
            docs = []
            for match in results.matches:
                metadata = match.metadata
                doc = {"id": match.id, **metadata}
                docs.append(doc)

            return docs

        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            raise StorageError(f"Search failed: {str(e)}")

    async def cleanup_namespace(self) -> None:
        """Clean up test namespace - only used in test environment"""
        if self.namespace != "test":
            self.logger.warning("Attempted to cleanup non-test namespace! Aborting.")
            return None

        try:
            self.pinecone_index.delete(namespace=self.namespace, delete_all=True)
            self.logger.info(f"Successfully cleaned up namespace {self.namespace}")
        except Exception as e:
            if "Namespace not found" in str(e):
                self.logger.info(f"Namespace {self.namespace} already clean")
            else:
                self.logger.error(
                    f"Failed to cleanup namespace {self.namespace}: {str(e)}"
                )

        return None
