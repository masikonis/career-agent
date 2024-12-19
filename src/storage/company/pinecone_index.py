import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

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
            # Initialize LangChain embeddings with proper model
            self.embeddings: Embeddings = OpenAIEmbeddings(
                model=config["LLM_MODELS"]["embeddings"]
            )

            # Initialize Pinecone
            self.pc = Pinecone(api_key=config["PINECONE_API_KEY"])

            # Setup index
            self.namespace = namespace
            self.index_name = "companies"

            # Create index if it doesn't exist
            existing_indexes = self.pc.list_indexes()
            if self.index_name not in [idx.name for idx in existing_indexes]:
                self.pc.create_index(
                    name=self.index_name,
                    dimension=1536,  # OpenAI embedding dimension
                    metric="cosine",
                )
                logger.info(f"Created new Pinecone index: {self.index_name}")

            # Get the index instance
            self.pinecone_index: Index = self.pc.Index(name=self.index_name)
            logger.info(
                f"Connected to Pinecone index: {self.index_name} namespace: {namespace}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {str(e)}")
            raise SearchIndexError(f"Pinecone initialization failed: {str(e)}")

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

            # Upsert to Pinecone using the index instance
            self.pinecone_index.upsert(
                vectors=[(str(entity_id), vector, metadata)], namespace=self.namespace
            )

            logger.info(f"Indexed company {entity_id} in namespace {self.namespace}")
            return True

        except Exception as e:
            logger.error(f"Failed to index company {entity_id}: {str(e)}")
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

            # Build filter conditions
            filter_conditions = {}
            if filters.industries:
                filter_conditions["industry"] = {
                    "$in": [i.value for i in filters.industries]
                }
            if filters.stages:
                filter_conditions["stage"] = {"$in": [s.value for s in filters.stages]}

            # Search with filters
            response = self.pinecone_index.query(
                namespace=self.namespace,
                vector=vector,
                top_k=limit,
                include_metadata=True,
                filter=filter_conditions if filter_conditions else None,
            )

            return [match.id for match in response.matches]

        except Exception as e:
            logger.error(f"Failed to search with filters: {str(e)}")
            return []
