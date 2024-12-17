from typing import List, Dict, Optional
import re
from difflib import SequenceMatcher
from collections import defaultdict
from src.utils.logger import get_logger
from .base import ProfileDataSource
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from src.config.settings import config

logger = get_logger(__name__)

class ProfileManager:
    """Manages access to profile data with advanced querying and analysis capabilities"""
    
    def __init__(self, data_source: ProfileDataSource):
        self.data_source = data_source
        self.level_weights = {
            'Expert': 1.0,
            'Advanced': 0.8,
            'Intermediate': 0.6,
            'Basic': 0.4
        }
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            model=config['LLM_MODELS']['embeddings']
        )
        self.vector_store = None
        logger.info("ProfileManager initialized")
    
    async def get_capabilities(self) -> List[Dict]:
        """Base method for raw capability access"""
        return await self.data_source.get_capabilities()
    
    async def get_capabilities_by_category(self, category: str) -> List[Dict]:
        """Get capabilities filtered by category"""
        capabilities = await self.get_capabilities()
        return [cap for cap in capabilities if cap['category'].lower() == category.lower()]

    async def get_capabilities_by_level(self, level: str) -> List[Dict]:
        """Get capabilities filtered by level"""
        logger.debug(f"Getting capabilities by level: {level}")
        capabilities = await self.get_capabilities()
        return [cap for cap in capabilities if cap['level'].lower() == level.lower()]

    async def get_top_capabilities(self, limit: int = 5) -> List[Dict]:
        """Get top capabilities (Expert/Advanced levels)"""
        logger.debug(f"Getting top capabilities with limit: {limit}")
        capabilities = await self.get_capabilities()
        top_levels = ['Expert', 'Advanced']
        top_caps = [cap for cap in capabilities if cap['level'] in top_levels]
        
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            logger.warning(f"Invalid limit value: {limit}, using default")
            limit = 5
            
        return sorted(
            top_caps, 
            key=lambda x: ['Expert', 'Advanced'].index(x['level'])
        )[:min(limit, len(top_caps))]

    async def search_capabilities(self, query: str, threshold: float = 0.2) -> List[Dict]:
        """Enhanced semantic search across capabilities"""
        logger.debug(f"Searching capabilities with query: {query}")
        
        if not query.strip():
            logger.debug("Empty search query, returning empty result")
            return []
            
        try:
            await self._initialize_vector_store()
            search_results = self.vector_store.similarity_search_with_score(
                query,
                k=5  # Return top 5 matches
            )
            
            matches = []
            for doc, score in search_results:
                if score >= threshold:
                    result = doc.metadata.copy()
                    result['match_score'] = float(score)
                    matches.append(result)
            
            return sorted(matches, key=lambda x: x['match_score'], reverse=True)
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}, falling back to traditional search")
            return await self._traditional_search(query, threshold)

    async def _traditional_search(self, query: str, threshold: float) -> List[Dict]:
        """Original search implementation as fallback"""
        capabilities = await self.get_capabilities()
        matches = []
        query = query.lower()
        
        for cap in capabilities:
            score = self._calculate_relevance_score(
                query,
                cap['name'],
                cap['experience'],
                cap['examples']
            )
            if score >= threshold:
                cap_with_score = cap.copy()
                cap_with_score['match_score'] = score
                matches.append(cap_with_score)
        
        return sorted(matches, key=lambda x: x['match_score'], reverse=True)

    async def match_requirements(self, requirements: List[str], weights: Optional[Dict] = None) -> Dict:
        """
        Match requirements against capabilities with semantic scoring
        Returns detailed matching analysis
        """
        logger.debug(f"Matching requirements: {requirements}")
        capabilities = await self.get_capabilities()
        weights = weights or self.level_weights
        
        matches = {
            'match_score': 0.0,
            'matched_skills': [],
            'partial_matches': [],
            'missing_skills': requirements.copy(),
            'additional_relevant': []
        }

        if not requirements:
            logger.debug("Empty requirements list provided")
            return matches
            
        try:
            await self._initialize_vector_store()
            
            for req in requirements:
                # Use semantic search to find best matches
                search_results = self.vector_store.similarity_search_with_score(
                    req,
                    k=3  # Get top 3 matches for each requirement
                )
                
                best_match = None
                best_score = 0
                
                for doc, score in search_results:
                    cap = doc.metadata.copy()
                    # Adjust score based on expertise level
                    adjusted_score = float(score) * weights[cap['level']]
                    
                    if adjusted_score > best_score:
                        best_score = adjusted_score
                        best_match = cap.copy()
                        best_match['match_score'] = adjusted_score

                if best_match:
                    if best_score >= 0.8:
                        matches['matched_skills'].append(best_match)
                        matches['missing_skills'].remove(req)
                    elif best_score >= 0.4:
                        matches['partial_matches'].append(best_match)
                        matches['missing_skills'].remove(req)
                        
                    # Find additional relevant capabilities
                    related = await self.find_related_capabilities(best_match['name'], min_similarity=0.6, k=2)
                    for rel in related:
                        if rel not in matches['additional_relevant']:
                            matches['additional_relevant'].append(rel)
                            
        except Exception as e:
            logger.error(f"Semantic matching failed: {e}, falling back to traditional matching")
            return await self._traditional_match_requirements(requirements, weights)

        total_reqs = len(requirements)
        matches['match_score'] = (
            (len(matches['matched_skills']) + 
             len(matches['partial_matches']) * 0.5) / total_reqs
            if total_reqs > 0 else 0.0
        )

        return matches

    async def _traditional_match_requirements(self, requirements: List[str], weights: Dict) -> Dict:
        """Original implementation as fallback"""
        capabilities = await self.get_capabilities()
        
        matches = {
            'match_score': 0.0,
            'matched_skills': [],
            'partial_matches': [],
            'missing_skills': requirements.copy(),
            'additional_relevant': []
        }

        if not requirements:
            return matches
            
        for req in requirements:
            best_match = None
            best_score = 0
            
            for cap in capabilities:
                score = self._calculate_relevance_score(
                    req.lower(),
                    cap['name'],
                    cap['experience'],
                    cap['examples']
                ) * weights[cap['level']]
                
                if score > best_score:
                    best_score = score
                    best_match = cap.copy()
                    best_match['match_score'] = score

            if best_score >= 0.8:
                matches['matched_skills'].append(best_match)
                matches['missing_skills'].remove(req)
            elif best_score >= 0.4:
                matches['partial_matches'].append(best_match)
                matches['missing_skills'].remove(req)

        total_reqs = len(requirements)
        matches['match_score'] = (
            (len(matches['matched_skills']) + 
             len(matches['partial_matches']) * 0.5) / total_reqs
            if total_reqs > 0 else 0.0
        )

        return matches

    async def get_expertise_distribution(self) -> Dict[str, List[Dict]]:
        """
        Simplified expertise distribution without semantic clustering.
        Using traditional grouping to avoid unnecessary embedding usage.
        """
        logger.debug("Generating expertise distribution using traditional grouping")
        capabilities = await self.get_capabilities()
        return self._get_expertise_distribution_traditional(capabilities)

    def _get_expertise_distribution_traditional(self, capabilities: List[Dict]) -> Dict[str, List[Dict]]:
        """Traditional expertise distribution"""
        distribution = {
            'Expert': [],
            'Advanced': [],
            'Intermediate': [],
            'Basic': []
        }
        
        for cap in capabilities:
            distribution[cap['level']].append(cap)
            
        return distribution

    def _get_category_breakdown(self, capabilities: List[Dict]) -> Dict[str, int]:
        """Helper method to get category distribution within a skill level"""
        breakdown = defaultdict(int)
        for cap in capabilities:
            breakdown[cap['category']] += 1
        return dict(breakdown)

    async def find_related_capabilities(self, capability_name: str, min_similarity: float = 0.3, k: int = 5) -> List[Dict]:
        """Find capabilities that are semantically related to the given one using embeddings"""
        logger.debug(f"Finding capabilities related to: {capability_name}")
        capabilities = await self.get_capabilities()
        target = next((cap for cap in capabilities if cap['name'].lower() == capability_name.lower()), None)
        
        if not target:
            logger.warning(f"Capability not found: {capability_name}")
            return []
        
        try:
            await self._initialize_vector_store()
            # Create query from target capability's details
            query = f"{target['name']}: {target['experience']} {target['examples']}"
            
            # Use FAISS to find similar capabilities
            search_results = self.vector_store.similarity_search_with_score(
                query,
                k=k + 1  # Add 1 to account for the query capability itself
            )
            
            related = []
            for doc, score in search_results:
                # Skip the capability itself
                if doc.metadata['name'] != capability_name:
                    if score >= min_similarity:
                        result = doc.metadata.copy()
                        result['similarity_score'] = float(score)
                        related.append(result)
                        
            return sorted(related, key=lambda x: x['similarity_score'], reverse=True)
            
        except Exception as e:
            logger.error(f"Semantic similarity search failed: {e}, falling back to traditional method")
            return await self._traditional_find_related(capability_name, min_similarity)

    async def _traditional_find_related(self, capability_name: str, min_similarity: float) -> List[Dict]:
        """Original implementation as fallback"""
        capabilities = await self.get_capabilities()
        target = next((cap for cap in capabilities if cap['name'].lower() == capability_name.lower()), None)
        
        if not target:
            return []
        
        related = []
        for cap in capabilities:
            if cap['name'] == capability_name:
                continue
            
            similarity = self._calculate_similarity(
                target['experience'] + ' ' + target['examples'],
                cap['experience'] + ' ' + cap['examples']
            )
            
            if similarity >= min_similarity:
                cap_with_score = cap.copy()
                cap_with_score['similarity_score'] = similarity
                related.append(cap_with_score)
                
        return sorted(related, key=lambda x: x['similarity_score'], reverse=True)

    async def generate_skill_summary(self, format: str = 'brief') -> Dict:
        """
        Generate capability summaries without using semantic embeddings.
        This avoids unnecessary complexity where simple grouping suffices.
        Formats: 'brief', 'detailed', 'technical', 'business'
        """
        logger.debug(f"Generating skill summary in format: {format}")
        capabilities = await self.get_capabilities()
        
        # Directly use traditional methods
        if format == 'brief':
            return self._generate_brief_summary_traditional(capabilities)
        elif format == 'detailed':
            return self._generate_detailed_summary_traditional(capabilities)
        elif format == 'technical':
            return self._generate_technical_summary_traditional(capabilities)
        elif format == 'business':
            return self._generate_business_summary_traditional(capabilities)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _generate_brief_summary_traditional(self, capabilities: List[Dict]) -> Dict:
        """Traditional brief summary implementation"""
        expert_caps = [cap for cap in capabilities if cap['level'] == 'Expert']
        advanced_caps = [cap for cap in capabilities if cap['level'] == 'Advanced']
        
        return {
            'top_expertise': [cap['name'] for cap in expert_caps],
            'advanced_skills': [cap['name'] for cap in advanced_caps],
            'total_capabilities': len(capabilities),
            'expertise_levels': {
                level: len([cap for cap in capabilities if cap['level'] == level])
                for level in self.level_weights.keys()
            }
        }

    def _generate_detailed_summary_traditional(self, capabilities: List[Dict]) -> Dict:
        """Traditional detailed summary implementation"""
        by_category = defaultdict(list)
        for cap in capabilities:
            by_category[cap['category']].append(cap)
            
        return {
            'categories': {
                category: {
                    'capabilities': caps,
                    'count': len(caps),
                    'levels': {
                        level: len([c for c in caps if c['level'] == level])
                        for level in self.level_weights.keys()
                    }
                }
                for category, caps in by_category.items()
            },
            'total_capabilities': len(capabilities),
            'category_distribution': {
                category: len(caps)
                for category, caps in by_category.items()
            }
        }

    def _generate_technical_summary_traditional(self, capabilities: List[Dict]) -> Dict:
        """Traditional technical summary implementation"""
        technical_cats = ['Hard Skills', 'Tools/Platforms']
        tech_caps = [
            cap for cap in capabilities 
            if cap['category'] in technical_cats
        ]
        
        return {
            'technical_expertise': {
                level: [cap for cap in tech_caps if cap['level'] == level]
                for level in self.level_weights.keys()
            },
            'core_technologies': [
                cap for cap in tech_caps 
                if cap['level'] in ['Expert', 'Advanced']
            ],
            'technical_breadth': len(tech_caps),
            'expertise_distribution': {
                level: len([cap for cap in tech_caps if cap['level'] == level])
                for level in self.level_weights.keys()
            }
        }

    def _generate_business_summary_traditional(self, capabilities: List[Dict]) -> Dict:
        """Traditional business summary implementation"""
        business_cats = ['Soft Skills', 'Domain Knowledge']
        business_caps = [
            cap for cap in capabilities 
            if cap['category'] in business_cats
        ]
        
        return {
            'key_strengths': [
                cap for cap in business_caps 
                if cap['level'] in ['Expert', 'Advanced']
            ],
            'domain_expertise': {
                'areas': [cap for cap in business_caps if cap['category'] == 'Domain Knowledge'],
                'soft_skills': [cap for cap in business_caps if cap['category'] == 'Soft Skills']
            },
            'expertise_levels': {
                level: [cap for cap in business_caps if cap['level'] == level]
                for level in self.level_weights.keys()
            }
        }

    def _calculate_relevance_score(self, query: str, name: str, experience: str, examples: str) -> float:
        """Calculate relevance score using text matching and similarity"""
        name_similarity = SequenceMatcher(None, query, name.lower()).ratio()
        content = f"{experience.lower()} {examples.lower()}"
        content_similarity = SequenceMatcher(None, query, content).ratio()
        keyword_bonus = 0.3 if query in content else 0
        score = (name_similarity * 0.6) + (content_similarity * 0.4) + keyword_bonus
        return min(1.0, score)

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts using a simple sequence matcher"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    async def _initialize_vector_store(self):
        """Initialize FAISS vector store with capability data, if needed"""
        if self.vector_store is not None:
            return

        capabilities = await self.get_capabilities()
        texts = [
            f"{cap['name']}: {cap['experience']} {cap['examples']}"
            for cap in capabilities
        ]
        
        try:
            self.vector_store = FAISS.from_texts(
                texts, 
                self.embeddings,
                metadatas=capabilities
            )
            logger.info("Vector store initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
