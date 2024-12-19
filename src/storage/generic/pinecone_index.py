import asyncio
from typing import Dict, List, Optional, Type

import pinecone
from langchain_openai import OpenAIEmbeddings

from src.config import config
from src.utils.logger import get_logger

from ..base.types import EntityID, Metadata
from .interfaces import GenericSearchIndex
from .types import T


class PineconeSearchIndex(GenericSearchIndex[T]):
    """Generic Pinecone search index implementation"""

    def __init__(self, namespace: str, entity_class: Type[T], is_test: bool = False):
        """Initialize Pinecone search index"""
        self.logger = get_logger(self.__class__.__name__.lower())
        self.namespace = f"{namespace}-test" if is_test else namespace
        self.entity_class = entity_class

        # Initialize embeddings using model from config
        self.embeddings = OpenAIEmbeddings(
            model=config["LLM_MODELS"]["embeddings"],
            openai_api_key=config["OPENAI_API_KEY"],
        )

        # Initialize Pinecone
        try:
            pinecone.init(
                api_key=config["PINECONE_API_KEY"], environment=config["PINECONE_ENV"]
            )

            index_name = config["PINECONE_INDEX_NAME"]
            if index_name not in pinecone.list_indexes():
                self.logger.info(f"Creating new index: {index_name}")
                pinecone.create_index(
                    name=index_name,
                    dimension=1536,  # OpenAI embedding dimension
                    metric="cosine",
                )

            self.pinecone_index = pinecone.Index(index_name)
            self.logger.info(f"Connected to Pinecone index: {index_name}")

        except Exception as e:
            self.logger.error(f"Failed to initialize Pinecone: {str(e)}")
            raise

    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using LangChain"""
        try:
            embedding = await self.embeddings.aembed_query(text)
            return embedding
        except Exception as e:
            self.logger.error(f"Failed to generate embedding: {str(e)}")
            raise

    async def index(self, entity_id: EntityID, entity: T, metadata: Metadata) -> bool:
        """Index an entity for search"""
        try:
            # Get search text from entity
            search_text = entity.get_search_text()

            # Generate embedding
            vector = await self._get_embedding(search_text)

            # Upsert to Pinecone
            self.pinecone_index.upsert(
                vectors=[(str(entity_id), vector, metadata)], namespace=self.namespace
            )

            # Verify indexing
            return await self.verify_indexing(entity_id)

        except Exception as e:
            self.logger.error(f"Failed to index entity {entity_id}: {str(e)}")
            return False

    async def verify_indexing(self, entity_id: EntityID, max_retries: int = 3) -> bool:
        """Verify that an entity was properly indexed"""
        for attempt in range(max_retries):
            await asyncio.sleep(2)
            try:
                result = self.pinecone_index.fetch(
                    ids=[str(entity_id)], namespace=self.namespace
                )
                if str(entity_id) in result["vectors"]:
                    return True
            except Exception as e:
                self.logger.warning(
                    f"Verification attempt {attempt + 1} failed: {str(e)}"
                )
        return False

    async def search(
        self, query: str, filters: Optional[Dict[str, any]] = None, limit: int = 10
    ) -> List[EntityID]:
        """Search for entities"""
        try:
            # Generate embedding for search query
            vector = await self._get_embedding(query)

            # Search in Pinecone
            response = self.pinecone_index.query(
                namespace=self.namespace,
                vector=vector,
                top_k=limit,
                include_metadata=True,
                filter=filters,
            )

            # Extract and return entity IDs
            results = [match.id for match in response.matches]
            self.logger.info(f"Search found {len(results)} results for query: {query}")
            return results

        except Exception as e:
            self.logger.error(f"Failed to search entities: {str(e)}")
            return []

    async def delete_from_index(self, entity_id: EntityID) -> bool:
        """Remove an entity from the search index"""
        try:
            self.pinecone_index.delete(ids=[str(entity_id)], namespace=self.namespace)
            self.logger.info(
                f"Deleted entity {entity_id} from namespace {self.namespace}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete entity {entity_id}: {str(e)}")
            return False

    async def find_similar(
        self, entity_id: EntityID, limit: int = 10
    ) -> List[EntityID]:
        """Find similar entities"""
        try:
            # Get the entity's vector
            result = self.pinecone_index.fetch(
                ids=[str(entity_id)], namespace=self.namespace
            )

            if not result or str(entity_id) not in result["vectors"]:
                self.logger.error(f"Entity {entity_id} not found in index")
                return []

            # Use the vector to find similar entities
            vector = result["vectors"][str(entity_id)]["values"]
            response = self.pinecone_index.query(
                namespace=self.namespace,
                vector=vector,
                top_k=limit + 1,  # +1 because the entity itself will be included
                include_metadata=True,
            )

            # Filter out the original entity
            similar_ids = []
            for match in response.matches:
                if match.id != str(entity_id):
                    similar_ids.append(match.id)

            return similar_ids[:limit]

        except Exception as e:
            self.logger.error(
                f"Failed to find similar entities for {entity_id}: {str(e)}"
            )
            return []

    async def cleanup_namespace(self):
        """Clean up all vectors in the namespace - should only be used in test environment"""
        if self.namespace.endswith("-test"):
            try:
                # Delete all vectors in the test namespace
                self.pinecone_index.delete(delete_all=True, namespace=self.namespace)
                self.logger.info(f"Cleaned up test namespace: {self.namespace}")
            except Exception as e:
                self.logger.error(f"Failed to cleanup test namespace: {str(e)}")
        else:
            self.logger.error("Cleanup can only be performed on test namespaces")
