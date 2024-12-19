import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import pinecone
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from pinecone import Index, Pinecone

from src.config import config
from src.storage.base.exceptions import SearchIndexError
from src.storage.base.types import EntityID, Metadata
from src.utils.logger import get_logger

from .interfaces import CompanySearchIndex
from .types import Company, CompanyFilters

logger = get_logger(__name__)


class PineconeCompanyIndex(CompanySearchIndex):
    """Pinecone implementation of company search index"""

    def __init__(self, namespace: str = "prod"):
        try:
            # Initialize OpenAI embeddings
            self.embeddings = OpenAIEmbeddings(model=config["LLM_MODELS"]["embeddings"])

            # Initialize Pinecone
            self.pc = Pinecone(api_key=config["PINECONE_API_KEY"])
            self.namespace = namespace
            self.index_name = "companies"

            # Get or create index
            try:
                self.pinecone_index = self.pc.Index(self.index_name)
                logger.info(f"Connected to existing index: {self.index_name}")
            except Exception:
                logger.info(f"Creating new index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name, dimension=1536, metric="cosine"
                )
                self.pinecone_index = self.pc.Index(self.index_name)

            logger.info(
                f"Connected to Pinecone index: {self.index_name} namespace: {namespace}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {str(e)}")
            raise SearchIndexError(f"Pinecone initialization failed: {str(e)}")

    async def cleanup_namespace(self) -> None:
        """Clean up test namespace - only used in test environment"""
        if self.namespace != "test":
            logger.warning("Attempted to cleanup non-test namespace! Aborting.")
            return None

        try:
            self.pinecone_index.delete(namespace=self.namespace, delete_all=True)
            logger.info(f"Successfully cleaned up namespace {self.namespace}")
        except Exception as e:
            if "Namespace not found" in str(e):
                logger.info(f"Namespace {self.namespace} already clean")
            else:
                logger.error(f"Failed to cleanup namespace {self.namespace}: {str(e)}")

        return None  # Explicit return to avoid NoneType error

    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text using LangChain"""
        try:
            vector = await self.embeddings.aembed_query(text)
            return vector

        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise SearchIndexError(f"Embedding generation failed: {str(e)}")

    async def add_to_index(
        self, entity_id: EntityID, company: Company, metadata: Metadata
    ) -> bool:
        """Index a company for search"""
        try:
            # Generate embedding from company description
            vector = await self._get_embedding(company.description)

            logger.info(f"Vector type: {type(vector)}, length: {len(vector)}")

            # Convert metadata to dict and ensure all values are strings
            metadata_dict = {
                k: str(v) if not isinstance(v, (int, float, bool, str)) else v
                for k, v in metadata.items()
            }

            logger.info(f"Upserting to namespace {self.namespace} with ID {entity_id}")
            logger.info(f"Vector dimensions: {len(vector)}")
            logger.info(f"Metadata: {metadata_dict}")

            # Upsert to Pinecone
            self.pinecone_index.upsert(
                vectors=[
                    {"id": str(entity_id), "values": vector, "metadata": metadata_dict}
                ],
                namespace=self.namespace,
            )

            # More lenient verification with longer delays
            max_retries = 5  # Increased from 3
            for attempt in range(max_retries):
                await asyncio.sleep(3)  # Increased from 2
                try:
                    # Try both fetch and search to verify
                    fetch_result = self.pinecone_index.fetch(
                        ids=[str(entity_id)], namespace=self.namespace
                    )

                    if str(entity_id) in fetch_result.vectors:
                        logger.info(
                            f"Successfully verified vector for {entity_id} (attempt {attempt + 1})"
                        )
                        return True

                    # Fallback to search if fetch doesn't find it
                    search_result = self.pinecone_index.query(
                        vector=vector,
                        top_k=1,
                        namespace=self.namespace,
                        include_metadata=True,
                    )

                    if search_result.matches and any(
                        m.id == str(entity_id) for m in search_result.matches
                    ):
                        logger.info(
                            f"Successfully verified vector via search for {entity_id} (attempt {attempt + 1})"
                        )
                        return True

                except Exception as e:
                    logger.warning(
                        f"Verification attempt {attempt + 1} failed: {str(e)}"
                    )
                    if attempt == max_retries - 1:
                        raise

            logger.error(
                f"Failed to verify upsert for {entity_id} after {max_retries} attempts"
            )
            return False

        except Exception as e:
            logger.error(f"Failed to add company {entity_id} to index: {str(e)}")
            logger.exception("Full error:")
            return False

    async def search(self, query: str, limit: int = 10) -> List[EntityID]:
        """Search for companies and return their IDs"""
        try:
            # Add a small delay to allow for indexing
            await asyncio.sleep(1)

            # Generate embedding for search query
            vector = await self._get_embedding(query)

            # Search in Pinecone using the index instance
            response = self.pinecone_index.query(
                namespace=self.namespace,
                vector=vector,
                top_k=limit,
                include_metadata=True,
            )

            # Extract and return company IDs
            results = [match.id for match in response.matches]
            logger.info(f"Search found {len(results)} results for query: {query}")
            return results

        except Exception as e:
            logger.error(f"Failed to search companies: {str(e)}")
            return []

    async def delete_from_index(self, entity_id: EntityID) -> bool:
        """Remove a company from the search index"""
        try:
            self.pinecone_index.delete(ids=[str(entity_id)], namespace=self.namespace)
            logger.info(f"Deleted company {entity_id} from namespace {self.namespace}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete company {entity_id}: {str(e)}")
            return False

    async def index(
        self, entity_id: EntityID, company: Company, metadata: Metadata
    ) -> bool:
        """Required implementation of abstract method"""
        return await self.add_to_index(entity_id, company, metadata)

    async def search_similar(
        self, company_id: EntityID, limit: int = 10
    ) -> List[Company]:
        """Find companies similar to the given company"""
        try:
            # Get the company's vector
            result = self.pinecone_index.fetch(
                ids=[str(company_id)], namespace=self.namespace
            )

            if not result or str(company_id) not in result["vectors"]:
                logger.error(f"Company {company_id} not found in index")
                return []

            # Use the vector to find similar companies
            vector = result["vectors"][str(company_id)]["values"]
            response = self.pinecone_index.query(
                namespace=self.namespace,
                vector=vector,
                top_k=limit + 1,  # +1 because the company itself will be included
                include_metadata=True,
            )

            # Filter out the original company and convert to Company objects
            similar_companies = []
            for match in response.matches:
                if match.id != str(company_id):  # Skip the original company
                    company_data = {"id": match.id, **match.metadata}
                    similar_companies.append(Company.from_dict(company_data))

            return similar_companies[:limit]

        except Exception as e:
            logger.error(f"Failed to find similar companies for {company_id}: {str(e)}")
            return []

    async def search_with_filters(
        self, query: str, filters: CompanyFilters, limit: int = 10
    ) -> List[EntityID]:
        """Search companies with specific filters"""
        try:
            # Generate embedding for the query
            vector = await self._get_embedding(query)

            # Search with filters
            response = self.pinecone_index.query(
                namespace=self.namespace,  # Make sure we're using the right namespace
                vector=vector,
                top_k=limit,
                include_metadata=True,
                filter=filters if filters else None,
            )

            # Log the results for debugging
            logger.info(
                f"Search in namespace {self.namespace} found {len(response.matches)} results"
            )
            for match in response.matches:
                logger.info(f"Found match: {match.id} in namespace {self.namespace}")

            return [match.id for match in response.matches]

        except Exception as e:
            logger.error(f"Failed to search with filters: {str(e)}")
            return []

    async def delete(self, entity_id: EntityID) -> bool:
        """Delete a company from the search index"""
        try:
            logger.info(f"Deleting company {entity_id} from namespace {self.namespace}")

            # Delete from Pinecone
            self.pinecone_index.delete(ids=[str(entity_id)], namespace=self.namespace)

            # Verify deletion
            for i in range(3):  # Try up to 3 times
                await asyncio.sleep(1)
                stats = self.pinecone_index.describe_index_stats()
                if str(entity_id) not in [
                    id for id in self.pinecone_index.fetch(ids=[str(entity_id)]).vectors
                ]:
                    logger.info(f"Successfully deleted company {entity_id}")
                    return True

            logger.error(f"Failed to verify deletion of company {entity_id}")
            return False

        except Exception as e:
            logger.error(f"Failed to delete company {entity_id}: {str(e)}")
            return False
