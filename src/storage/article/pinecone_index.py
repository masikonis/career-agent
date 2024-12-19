import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_openai import OpenAIEmbeddings
from pinecone import Index, Pinecone

from src.config import config
from src.utils.logger import get_logger

from ..base.exceptions import SearchError, SearchIndexError
from ..base.types import EntityID
from .interfaces import ArticleSearchIndex
from .types import Article, ArticleFilters

logger = get_logger(__name__)


class ArticlePineconeIndex(ArticleSearchIndex):
    """Pinecone implementation of article search index"""

    def __init__(self, namespace: str = "prod"):
        try:
            # Initialize OpenAI embeddings
            self.embeddings = OpenAIEmbeddings(model=config["LLM_MODELS"]["embeddings"])

            # Initialize Pinecone
            self.pc = Pinecone(api_key=config["PINECONE_API_KEY"])
            self.namespace = namespace
            self.index_name = "articles"

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

    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text using LangChain"""
        try:
            vector = await self.embeddings.aembed_query(text)
            return vector

        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise SearchIndexError(f"Embedding generation failed: {str(e)}")

    async def index(
        self, entity_id: EntityID, article: Article, metadata: Dict[str, Any]
    ) -> bool:
        """Index an article for search"""
        try:
            # Generate embedding from article content
            vector = await self._get_embedding(article.get_search_text())

            # Convert metadata to dict and ensure all values are strings
            metadata_dict = {
                k: str(v) if not isinstance(v, (int, float, bool, str)) else v
                for k, v in metadata.items()
            }

            # Upsert to Pinecone
            self.pinecone_index.upsert(
                vectors=[
                    {"id": str(entity_id), "values": vector, "metadata": metadata_dict}
                ],
                namespace=self.namespace,
            )

            # Verify upsert with retries
            max_retries = 5
            for attempt in range(max_retries):
                await asyncio.sleep(3)
                try:
                    fetch_result = self.pinecone_index.fetch(
                        ids=[str(entity_id)], namespace=self.namespace
                    )

                    if str(entity_id) in fetch_result.vectors:
                        logger.info(
                            f"Successfully verified vector for {entity_id} (attempt {attempt + 1})"
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
            logger.error(f"Failed to add article {entity_id} to index: {str(e)}")
            logger.exception("Full error:")
            return False

    async def search(self, query: str, limit: int = 10) -> List[EntityID]:
        """Search for articles and return their IDs"""
        try:
            # Add a small delay to allow for indexing
            await asyncio.sleep(1)

            # Generate embedding for search query
            vector = await self._get_embedding(query)

            # Search in Pinecone
            response = self.pinecone_index.query(
                namespace=self.namespace,
                vector=vector,
                top_k=limit,
                include_metadata=True,
            )

            results = [match.id for match in response.matches]
            logger.info(f"Search found {len(results)} results for query: {query}")
            return results

        except Exception as e:
            logger.error(f"Failed to search articles: {str(e)}")
            return []

    async def delete_from_index(self, entity_id: EntityID) -> bool:
        """Remove an article from the search index"""
        try:
            self.pinecone_index.delete(ids=[str(entity_id)], namespace=self.namespace)
            logger.info(f"Deleted article {entity_id} from namespace {self.namespace}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete article {entity_id}: {str(e)}")
            return False

    async def find_similar(
        self, article_id: EntityID, limit: int = 10
    ) -> List[EntityID]:
        """Find articles similar to the given article"""
        try:
            # Get the article's vector
            result = self.pinecone_index.fetch(
                ids=[str(article_id)], namespace=self.namespace
            )

            if not result or str(article_id) not in result.vectors:
                logger.error(f"Article {article_id} not found in index")
                return []

            # Use the vector to find similar articles
            vector = result.vectors[str(article_id)].values
            response = self.pinecone_index.query(
                namespace=self.namespace,
                vector=vector,
                top_k=limit + 1,  # +1 because the article itself will be included
                include_metadata=True,
            )

            # Filter out the original article
            similar_ids = [
                match.id for match in response.matches if match.id != str(article_id)
            ]

            return similar_ids[:limit]

        except Exception as e:
            logger.error(f"Failed to find similar articles for {article_id}: {str(e)}")
            return []
