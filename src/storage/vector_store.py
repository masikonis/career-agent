from typing import Dict, List, Optional
import chromadb
from datetime import datetime, UTC
import json

class StartupVectorStore:
    def __init__(self, persist_directory: str = "./data/vectordb"):
        """Initialize ChromaDB client with persistence"""
        self.client = chromadb.PersistentClient(path=persist_directory)
        # Create or get collection with embeddings config
        self.collection = self.client.get_or_create_collection(
            name="startups",
            metadata={"hnsw:space": "cosine"},
            embedding_function=chromadb.utils.embedding_functions.DefaultEmbeddingFunction()  # Using default embeddings
        )

    async def add_startup(self, 
                         startup_id: str,
                         name: str,
                         description: str,
                         metadata: Dict) -> None:
        """Add a startup to the vector store"""
        # Add timestamp and other metadata
        metadata.update({
            'startup_id': startup_id,
            'name': name,
            'added_at': datetime.now(UTC).isoformat(),
            'evaluated': False
        })
        
        # Add to collection
        self.collection.add(
            documents=[description],
            metadatas=[metadata],
            ids=[startup_id]
        )

    async def get_startup(self, startup_id: str) -> Optional[Dict]:
        """Retrieve a startup by ID"""
        try:
            result = self.collection.get(
                ids=[startup_id],
                include=['metadatas', 'documents']
            )
            if result and result['metadatas']:
                return {
                    'metadata': result['metadatas'][0],
                    'description': result['documents'][0]
                }
        except Exception as e:
            print(f"Error retrieving startup: {e}")
        return None

    async def mark_as_evaluated(self, 
                              startup_id: str, 
                              evaluation_result: Dict) -> None:
        """Mark a startup as evaluated with results"""
        startup = await self.get_startup(startup_id)
        if startup:
            # Get current data
            metadata = startup['metadata']
            description = startup['description']
            
            # Update metadata
            metadata.update({
                'evaluated': True,
                'evaluated_at': datetime.now(UTC).isoformat(),
                'evaluation_result': json.dumps(evaluation_result)
            })
            
            # Update in collection
            self.collection.upsert(
                ids=[startup_id],
                metadatas=[metadata],
                documents=[description]
            )

    async def get_similar_startups(self, 
                                 description: str, 
                                 n_results: int = 5) -> List[Dict]:
        """Find similar startups based on description"""
        results = self.collection.query(
            query_texts=[description],
            n_results=n_results,
            include=['metadatas', 'documents', 'distances']
        )
        
        return [{
            'description': doc,
            'metadata': meta,
            'distance': dist
        } for doc, meta, dist in zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )]

    async def get_unevaluated_startups(self) -> List[Dict]:
        """Get all startups that haven't been evaluated yet"""
        results = self.collection.get(
            where={"evaluated": False},
            include=['metadatas', 'documents']
        )
        
        if results['ids']:
            return [{
                'metadata': meta,
                'description': doc
            } for doc, meta in zip(
                results['documents'],
                results['metadatas']
            )]
        return [] 