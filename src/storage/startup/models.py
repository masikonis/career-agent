from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum
import json

class StartupStage(Enum):
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C = "series_c"
    GROWTH = "growth"
    IPO = "ipo"

class StartupIndustry(Enum):
    AI = "artificial_intelligence"
    FINTECH = "financial_technology"
    HEALTHTECH = "health_technology"
    EDTECH = "education_technology"
    ECOMMERCE = "e_commerce"
    OTHER = "other"

@dataclass
class StartupEvaluation:
    """Evaluation results for a startup"""
    match_score: float
    skills_match: List[str]
    notes: Optional[str] = None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now())

@dataclass
class Startup:
    """Represents a startup entity"""
    id: str
    name: str
    description: str
    industry: StartupIndustry
    stage: StartupStage
    team_size: Optional[int] = None
    tech_stack: List[str] = field(default_factory=list)
    funding_amount: Optional[float] = None
    evaluation: Optional[StartupEvaluation] = None
    added_at: datetime = field(default_factory=lambda: datetime.now())
    
    def to_dict(self) -> Dict:
        """Convert startup to dictionary format with serialized values"""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'industry': self.industry.value,  # Convert enum to string
            'stage': self.stage.value,        # Convert enum to string
            'team_size': self.team_size,
            'tech_stack': ','.join(self.tech_stack),  # Convert list to string
            'funding_amount': self.funding_amount,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'evaluation': json.dumps(self.evaluation.__dict__) if self.evaluation else None
        }
        # Remove None values as ChromaDB doesn't accept them
        return {k: v for k, v in data.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Startup':
        """Create Startup instance from dictionary with deserialized values"""
        # Deep copy to avoid modifying input
        data = data.copy()
        
        # Convert string back to list for tech_stack
        if 'tech_stack' in data:
            data['tech_stack'] = data['tech_stack'].split(',') if data['tech_stack'] else []
            
        # Convert string back to enum
        if 'industry' in data:
            data['industry'] = StartupIndustry(data['industry'])
        if 'stage' in data:
            data['stage'] = StartupStage(data['stage'])
            
        # Parse dates
        if 'added_at' in data and data['added_at']:
            data['added_at'] = datetime.fromisoformat(data['added_at'])
            
        # Parse evaluation
        if 'evaluation' in data and data['evaluation']:
            if isinstance(data['evaluation'], str):
                data['evaluation'] = json.loads(data['evaluation'])
            data['evaluation'] = StartupEvaluation(**data['evaluation'])
            
        return cls(**data) 