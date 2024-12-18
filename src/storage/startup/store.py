from typing import Dict, List, Optional, Any
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from src.utils.logger import get_logger
from src.config.settings import config
from ..base import VectorStore
from .models import Startup
import asyncio

logger = get_logger(__name__)

class StartupVectorStore(VectorStore):
    """Vector store for startup data using Pinecone"""

    def __init__(self, namespace: str = "prod"):
        """Initialize Pinecone client and index"""
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            model=config['LLM_MODELS']['embeddings']
        )
        
        # Initialize Pinecone with new SDK pattern
        self.pc = Pinecone(api_key=config['PINECONE_API_KEY'])
        
        # Get or create index
        self.namespace = namespace
        index_name = "startups"
        existing_indexes = self.pc.list_indexes().names()
        
        if index_name not in existing_indexes:
            self.pc.create_index(
                name=index_name,
                dimension=1536,  # OpenAI embedding dimension
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region='us-east-1'
                )
            )
            logger.info(f"Created new Pinecone index: {index_name}")
        
        # Get index instance
        self.index = self.pc.Index(index_name)
        logger.info(f"Connected to Pinecone index: {index_name} with namespace: {namespace}")

    async def add_item(self, item_id: str, content: str, metadata: Dict[str, Any]) -> None:
        """Implement abstract method: Add an item to vector store"""
        try:
            vector = await self.embeddings.aembed_query(content)
            metadata['description'] = content
            
            logger.debug(f"Adding item {item_id} with metadata: {metadata} to namespace {self.namespace}")
            
            self.index.upsert(
                vectors=[(
                    item_id,
                    vector,
                    metadata
                )],
                namespace=self.namespace
            )
            logger.info(f"Successfully added item {item_id} to namespace {self.namespace}")
        except Exception as e:
            logger.error(f"Error adding item {item_id} in namespace {self.namespace}: {e}")
            raise

    async def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Implement abstract method: Get item by ID"""
        try:
            result = self.index.fetch(
                ids=[item_id],
                namespace=self.namespace
            )
            logger.debug(f"Fetch result for {item_id} in namespace {self.namespace}: {result}")
            
            if result and result['vectors']:
                vector_data = result['vectors'].get(item_id)
                if vector_data and vector_data.metadata:
                    return {
                        'id': item_id,
                        **vector_data.metadata
                    }
            logger.warning(f"No data found for item {item_id} in namespace {self.namespace}")
            return None
        except Exception as e:
            logger.error(f"Error getting item {item_id} from namespace {self.namespace}: {e}")
            raise

    async def update_item(self, item_id: str, metadata: Dict[str, Any]) -> bool:
        """Implement abstract method: Update item"""
        try:
            content = metadata.get('description', '')
            logger.debug(f"Updating item {item_id} with metadata: {metadata}")
            
            # Get new embedding for updated content
            vector = await self.embeddings.aembed_query(content)
            
            # Upsert with new vector and metadata
            self.index.upsert(
                vectors=[(
                    item_id,
                    vector,
                    metadata
                )]
            )
            logger.info(f"Successfully updated item {item_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating item {item_id}: {e}")
            return False

    async def delete_item(self, item_id: str) -> bool:
        """Implement abstract method: Delete item"""
        try:
            self.index.delete(
                ids=[item_id],
                namespace=self.namespace
            )
            logger.info(f"Successfully deleted item {item_id} from namespace {self.namespace}")
            return True
        except Exception as e:
            logger.error(f"Error deleting item {item_id} from namespace {self.namespace}: {e}")
            return False

    async def add_startup(self, startup: Startup) -> None:
        """Add a startup to the vector store"""
        try:
            metadata = startup.to_dict()
            logger.debug(f"Adding startup {startup.id} to namespace {self.namespace}")
            logger.debug(f"Metadata: {metadata}")
            
            vector = await self.embeddings.aembed_query(startup.description)
            logger.debug(f"Generated vector of length: {len(vector)}")
            
            # Upsert to Pinecone
            upsert_response = self.index.upsert(
                vectors=[(
                    startup.id,
                    vector,
                    metadata
                )],
                namespace=self.namespace
            )
            logger.debug(f"Upsert response: {upsert_response}")
            
            # Wait longer for Pinecone to process
            await asyncio.sleep(3)
            
            # Verify with retries
            max_retries = 3
            for i in range(max_retries):
                result = self.index.fetch(
                    ids=[startup.id],
                    namespace=self.namespace
                )
                logger.debug(f"Verification attempt {i+1}, result: {result}")
                
                if result and result['vectors'] and startup.id in result['vectors']:
                    logger.info(f"Successfully verified startup {startup.id} in namespace {self.namespace}")
                    return
                
                if i < max_retries - 1:
                    await asyncio.sleep(2)
            
            raise Exception(f"Verification failed for startup {startup.id} in namespace {self.namespace} after {max_retries} attempts")
            
        except Exception as e:
            logger.error(f"Error adding startup {startup.id} to namespace {self.namespace}: {e}")
            raise

    async def get_startup(self, startup_id: str) -> Optional[Startup]:
        """Get a startup by ID"""
        try:
            logger.debug(f"Fetching startup {startup_id} from namespace {self.namespace}")
            result = self.index.fetch(
                ids=[startup_id],
                namespace=self.namespace
            )
            logger.debug(f"Fetch result: {result}")
            
            if result and result['vectors']:
                vector_data = result['vectors'].get(startup_id)
                if vector_data and vector_data.metadata:
                    startup_data = {
                        'id': startup_id,
                        **vector_data.metadata
                    }
                    logger.debug(f"Reconstructed startup data: {startup_data}")
                    return Startup.from_dict(startup_data)
            
            logger.warning(f"No data found for startup {startup_id} in namespace {self.namespace}")
            return None
        except Exception as e:
            logger.error(f"Error getting startup {startup_id} from namespace {self.namespace}: {e}")
            return None

    async def update_startup(self, startup: Startup) -> bool:
        """Update a startup's data"""
        try:
            metadata = startup.to_dict()
            logger.debug(f"Updating startup {startup.id} in namespace {self.namespace}")
            logger.debug(f"Update metadata: {metadata}")
            
            # Get new embedding for updated description
            vector = await self.embeddings.aembed_query(startup.description)
            logger.debug(f"Generated update vector of length: {len(vector)}")
            
            # Direct upsert to Pinecone
            upsert_response = self.index.upsert(
                vectors=[(
                    startup.id,
                    vector,
                    metadata
                )],
                namespace=self.namespace
            )
            logger.debug(f"Update upsert response: {upsert_response}")
            
            # Wait longer for Pinecone to process
            await asyncio.sleep(3)
            
            # Verify with retries
            max_retries = 3
            for i in range(max_retries):
                result = self.index.fetch(
                    ids=[startup.id],
                    namespace=self.namespace
                )
                logger.debug(f"Update verification attempt {i+1}, result: {result}")
                
                if result and result['vectors'] and startup.id in result['vectors']:
                    vector_data = result['vectors'][startup.id]
                    if vector_data.metadata.get('description') == startup.description:
                        logger.info(f"Successfully verified startup update {startup.id} in namespace {self.namespace}")
                        return True
                
                if i < max_retries - 1:
                    logger.debug(f"Verification attempt {i+1} failed, waiting before retry...")
                    await asyncio.sleep(2)
            
            raise Exception(f"Update verification failed for startup {startup.id} in namespace {self.namespace} after {max_retries} attempts")
            
        except Exception as e:
            logger.error(f"Error updating startup {startup.id} in namespace {self.namespace}: {e}")
            return False

    async def find_similar(self, content: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Find similar startups based on content"""
        try:
            query_vector = await self.embeddings.aembed_query(content)
            results = self.index.query(
                vector=query_vector,
                top_k=n_results,
                include_metadata=True,
                namespace=self.namespace
            )
            
            similar_startups = []
            for match in results.matches:
                startup_data = {
                    'id': match.id,
                    'score': match.score,
                    **match.metadata
                }
                similar_startups.append(startup_data)
            
            return similar_startups
        except Exception as e:
            logger.error(f"Error finding similar startups in namespace {self.namespace}: {e}")
            raise
