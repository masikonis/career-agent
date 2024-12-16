from typing import Dict, List, Optional, Any
from datetime import datetime
import chromadb
from ..base import VectorStore
from .models import Startup, StartupEvaluation, StartupIndustry, StartupStage
import json

class StartupVectorStore(VectorStore):
    """Vector store for startup data"""

    def __init__(self, persist_directory: str = "./data/startups"):
        """Initialize ChromaDB client with persistence"""
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name="startups",
            metadata={"hnsw:space": "cosine"},
            embedding_function=chromadb.utils.embedding_functions.DefaultEmbeddingFunction()
        )

    async def add_startup(self, startup: Startup) -> None:
        """Add a startup to the vector store using the Startup model"""
        metadata = startup.to_dict()
        await self.add_item(startup.id, startup.description, metadata)

    async def get_startup(self, startup_id: str) -> Optional[Startup]:
        """Get a startup by ID and return as Startup model"""
        item = await self.get_item(startup_id)
        if item:
            # Clean metadata before creating Startup
            startup_data = {
                'id': item['metadata'].get('id'),
                'name': item['metadata'].get('name'),
                'description': item['description'],
                'industry': item['metadata'].get('industry'),
                'stage': item['metadata'].get('stage'),
                'team_size': item['metadata'].get('team_size'),
                'tech_stack': item['metadata'].get('tech_stack'),
                'funding_amount': item['metadata'].get('funding_amount'),
                'added_at': item['metadata'].get('added_at'),
                'evaluation': item['metadata'].get('evaluation')
            }
            return Startup.from_dict(startup_data)
        return None

    async def update_startup(self, startup: Startup) -> bool:
        """Update a startup using the Startup model"""
        return await self.update_item(startup.id, startup.to_dict())

    async def add_evaluation(self, startup_id: str, evaluation: StartupEvaluation) -> bool:
        """Add evaluation to a startup"""
        eval_data = {
            'evaluation': json.dumps({
                'match_score': evaluation.match_score,
                'skills_match': ','.join(evaluation.skills_match),
                'notes': evaluation.notes,
                'evaluated_at': evaluation.evaluated_at.isoformat()
            }),
            'evaluated_at': datetime.now().isoformat()
        }
        return await self.update_item(startup_id, eval_data)

    async def find_similar_startups(self, description: str, n_results: int = 5) -> List[Startup]:
        """Find similar startups and return as Startup models"""
        results = await self.find_similar(description, n_results)
        return [
            Startup.from_dict({**result['metadata'], 'description': result['description']})
            for result in results
        ]

    async def get_by_industry(self, industry: StartupIndustry) -> List[Startup]:
        """Get all startups in a specific industry"""
        results = self.collection.get(
            where={"industry": industry.value},
            include=['metadatas', 'documents']
        )
        return [
            Startup.from_dict({**meta, 'description': doc})
            for meta, doc in zip(results['metadatas'], results['documents'])
        ]

    async def get_by_stage(self, stage: StartupStage) -> List[Startup]:
        """Get all startups at a specific stage"""
        results = self.collection.get(
            where={"stage": stage.value},
            include=['metadatas', 'documents']
        )
        return [
            Startup.from_dict({**meta, 'description': doc})
            for meta, doc in zip(results['metadatas'], results['documents'])
        ]

    async def get_by_tech_stack(self, tech: str) -> List[Startup]:
        """Get startups by tech stack"""
        # First get all startups
        results = self.collection.get(
            include=['metadatas', 'documents']
        )
        
        if not results['ids']:
            return []

        # Then filter by tech stack manually
        startups = []
        for meta, doc in zip(results['metadatas'], results['documents']):
            tech_stack = meta.get('tech_stack', '').split(',')
            if tech in tech_stack:
                startups.append(Startup.from_dict({**meta, 'description': doc}))
        
        return startups

    async def get_unevaluated_startups(self) -> List[Startup]:
        """Get all startups that haven't been evaluated"""
        # First get all startups
        results = self.collection.get(
            include=['metadatas', 'documents']
        )
        
        if not results['ids']:
            return []

        # Then filter manually
        startups = []
        for meta, doc in zip(results['metadatas'], results['documents']):
            if 'evaluation' not in meta or not meta['evaluation']:
                startup_data = {
                    'id': meta.get('id'),
                    'name': meta.get('name'),
                    'description': doc,
                    'industry': meta.get('industry'),
                    'stage': meta.get('stage'),
                    'team_size': meta.get('team_size'),
                    'tech_stack': meta.get('tech_stack'),
                    'funding_amount': meta.get('funding_amount'),
                    'added_at': meta.get('added_at')
                }
                startups.append(Startup.from_dict(startup_data))
        
        return startups

    async def get_evaluated_startups(self, min_score: float = 0.0) -> List[Startup]:
        """Get evaluated startups with minimum match score"""
        # First get all startups
        results = self.collection.get(
            include=['metadatas', 'documents']
        )
        
        if not results['ids']:
            return []

        # Then filter manually
        startups = []
        for meta, doc in zip(results['metadatas'], results['documents']):
            evaluation_str = meta.get('evaluation')
            if evaluation_str:
                try:
                    evaluation = json.loads(evaluation_str)
                    if evaluation.get('match_score', 0.0) >= min_score:
                        # Clean metadata before creating Startup
                        startup_data = {
                            'id': meta.get('id'),
                            'name': meta.get('name'),
                            'description': doc,
                            'industry': meta.get('industry'),
                            'stage': meta.get('stage'),
                            'team_size': meta.get('team_size'),
                            'tech_stack': meta.get('tech_stack'),
                            'funding_amount': meta.get('funding_amount'),
                            'added_at': meta.get('added_at'),
                            'evaluation': evaluation_str
                        }
                        startups.append(Startup.from_dict(startup_data))
                except json.JSONDecodeError:
                    continue
        
        return startups

    # Base class implementations
    async def add_item(self, item_id: str, content: str, metadata: Dict[str, Any]) -> None:
        """Add a startup to the vector store"""
        if not isinstance(metadata.get('added_at'), str):
            metadata['added_at'] = datetime.now().isoformat()
        
        self.collection.add(
            documents=[content],
            metadatas=[metadata],
            ids=[item_id]
        )

    async def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a startup by ID"""
        try:
            result = self.collection.get(
                ids=[item_id],
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

    async def update_item(self, item_id: str, metadata: Dict[str, Any]) -> bool:
        """Update a startup's metadata"""
        try:
            current = await self.get_item(item_id)
            if current:
                updated_metadata = {**current['metadata'], **metadata}
                self.collection.upsert(
                    ids=[item_id],
                    metadatas=[updated_metadata],
                    documents=[current['description']]
                )
                return True
        except Exception as e:
            print(f"Error updating startup: {e}")
        return False

    async def find_similar(self, content: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Find similar startups based on description"""
        results = self.collection.query(
            query_texts=[content],
            n_results=n_results,
            include=['metadatas', 'documents', 'distances']
        )
        
        return [{
            'description': doc,
            'metadata': meta,
            'similarity': 1 - dist  # Convert distance to similarity score
        } for doc, meta, dist in zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )]

    async def delete_item(self, item_id: str) -> bool:
        """Delete a startup from the store"""
        try:
            self.collection.delete(ids=[item_id])
            return True
        except Exception as e:
            print(f"Error deleting startup: {e}")
            return False
    
    # Implementation of abstract methods... 