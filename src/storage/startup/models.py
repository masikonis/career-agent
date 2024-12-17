from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum
import json

class StartupStage(Enum):
    """Startup stages focused on early-stage opportunities"""
    IDEA = "idea"                # Just an idea, pre-MVP
    PRE_SEED = "pre_seed"        # Working on MVP
    MVP = "mvp"                  # Has MVP, seeking validation
    SEED = "seed"                # Has traction, raising seed
    EARLY = "early"              # Post-seed, early revenue
    SERIES_A = "series_a"        # Scaling up
    LATER = "later"              # Beyond Series A (less relevant)

class StartupIndustry(Enum):
    """Digital-first industries where marketing drives growth"""
    EDTECH = "education"         # Direct experience
    AGENCY = "agency"            # Direct experience
    SAAS = "saas"                # Any vertical, marketing-driven
    MARKETPLACE = "marketplace"  # Two-sided platforms
    CONTENT = "content"          # Content-driven businesses
    D2C = "d2c"                  # Direct-to-consumer digital
    NON_DIGITAL = "non_digital"  # Not primarily digital or marketing-driven

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
    evaluation: Optional[StartupEvaluation] = None
    added_at: datetime = field(default_factory=lambda: datetime.now())
    
    def to_dict(self) -> Dict:
        """Convert startup to dictionary format"""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'industry': self.industry.value,
            'stage': self.stage.value,
            'added_at': self.added_at.isoformat()
        }
        
        # Only add evaluation if it exists
        if self.evaluation:
            data['evaluation'] = json.dumps(self.evaluation.__dict__)
            
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Startup':
        """Create Startup instance from dictionary"""
        # Deep copy to avoid modifying input
        data = data.copy()
        
        # Parse evaluation if it exists
        if 'evaluation' in data and data['evaluation']:
            if isinstance(data['evaluation'], str):
                evaluation_dict = json.loads(data['evaluation'])
                # Convert comma-separated skills back to list
                if 'skills_match' in evaluation_dict and isinstance(evaluation_dict['skills_match'], str):
                    evaluation_dict['skills_match'] = evaluation_dict['skills_match'].split(',')
                # Parse evaluated_at datetime
                if 'evaluated_at' in evaluation_dict:
                    evaluation_dict['evaluated_at'] = datetime.fromisoformat(evaluation_dict['evaluated_at'])
                data['evaluation'] = StartupEvaluation(**evaluation_dict)
        
        # Parse dates
        if 'added_at' in data:
            data['added_at'] = datetime.fromisoformat(data['added_at'])
        
        # Convert string back to enum
        data['industry'] = StartupIndustry(data['industry'])
        data['stage'] = StartupStage(data['stage'])
        
        return cls(**data)
