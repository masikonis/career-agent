from typing import List, Dict, Optional
import re
from difflib import SequenceMatcher
from collections import defaultdict
from src.utils.logger import get_logger
from .base import ProfileDataSource

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
        capabilities = await self.get_capabilities()
        
        if not query.strip():
            logger.debug("Empty search query, returning empty result")
            return []
            
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
        Match requirements against capabilities with scoring
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
            len(matches['matched_skills']) + 
            len(matches['partial_matches']) * 0.5
        ) / total_reqs

        return matches

    async def get_expertise_distribution(self) -> Dict[str, List[Dict]]:
        """Group capabilities by expertise level with rich metadata"""
        logger.debug("Generating expertise distribution")
        capabilities = await self.get_capabilities()
        distribution = {
            'Expert': [],
            'Advanced': [],
            'Intermediate': [],
            'Basic': []
        }
        
        for cap in capabilities:
            distribution[cap['level']].append(cap)
            
        return distribution

    async def find_related_capabilities(self, capability_name: str, min_similarity: float = 0.3) -> List[Dict]:
        """Find capabilities that are semantically related to the given one"""
        logger.debug(f"Finding capabilities related to: {capability_name}")
        capabilities = await self.get_capabilities()
        target = next((cap for cap in capabilities if cap['name'].lower() == capability_name.lower()), None)
        
        if not target:
            logger.warning(f"Capability not found: {capability_name}")
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
        Generate capability summaries at different detail levels
        Formats: 'brief', 'detailed', 'technical', 'business'
        """
        logger.debug(f"Generating skill summary in format: {format}")
        capabilities = await self.get_capabilities()
        
        if format == 'brief':
            return self._generate_brief_summary(capabilities)
        elif format == 'detailed':
            return self._generate_detailed_summary(capabilities)
        elif format == 'technical':
            return self._generate_technical_summary(capabilities)
        elif format == 'business':
            return self._generate_business_summary(capabilities)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _calculate_relevance_score(self, query: str, name: str, experience: str, examples: str) -> float:
        """Calculate relevance score using text matching and similarity"""
        # Direct name match has highest weight
        name_similarity = SequenceMatcher(None, query, name.lower()).ratio()
        
        # Content match has lower weight
        content = f"{experience.lower()} {examples.lower()}"
        content_similarity = SequenceMatcher(None, query, content).ratio()
        
        # Keyword presence adds bonus
        keyword_bonus = 0.3 if query in content else 0
        
        # Combined score with weights
        score = (name_similarity * 0.6) + (content_similarity * 0.4) + keyword_bonus
        return min(1.0, score)

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts"""
        # Using sequence matcher for basic similarity
        # Could be enhanced with more sophisticated NLP techniques
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def _generate_brief_summary(self, capabilities: List[Dict]) -> Dict:
        """Generate brief capability summary"""
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

    def _generate_detailed_summary(self, capabilities: List[Dict]) -> Dict:
        """Generate detailed capability summary"""
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

    def _generate_technical_summary(self, capabilities: List[Dict]) -> Dict:
        """Generate technical-focused summary"""
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

    def _generate_business_summary(self, capabilities: List[Dict]) -> Dict:
        """Generate business-focused summary"""
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
