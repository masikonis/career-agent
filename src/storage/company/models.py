import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class CompanyStage(Enum):
    """Company stages focused on early-stage opportunities"""
    IDEA = "idea"                # Just an idea, pre-MVP
    PRE_SEED = "pre_seed"        # Working on MVP
    MVP = "mvp"                  # Has MVP, seeking validation
    SEED = "seed"                # Has traction, raising seed
    EARLY = "early"              # Post-seed, early revenue
    SERIES_A = "series_a"        # Scaling up
    LATER = "later"              # Beyond Series A (less relevant)

class CompanyIndustry(Enum):
    """Digital-first industries where marketing drives growth"""
    EDTECH = "education"         # Direct experience
    AGENCY = "agency"            # Direct experience
    SAAS = "saas"                # Any vertical, marketing-driven
    MARKETPLACE = "marketplace"  # Two-sided platforms
    CONTENT = "content"          # Content-driven businesses
    D2C = "d2c"                  # Direct-to-consumer digital
    NON_DIGITAL = "non_digital"  # Not primarily digital or marketing-driven

@dataclass
class CompanyEvaluation:
    """Evaluation results for a company"""
    match_score: float
    skills_match: List[str]
    notes: Optional[str] = None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now())

@dataclass
class Company:
    """Represents a company entity"""
    id: str
    name: str
    description: str
    industry: CompanyIndustry
    stage: CompanyStage
    evaluations: List[CompanyEvaluation] = field(default_factory=list)
    added_at: datetime = field(default_factory=lambda: datetime.now())
    
    def to_dict(self) -> Dict:
        """Convert company to dictionary format"""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'industry': self.industry.value,
            'stage': self.stage.value,
            'added_at': self.added_at.isoformat(),
            'evaluations': json.dumps([
                {
                    'match_score': eval.match_score,
                    'skills_match': eval.skills_match,
                    'notes': eval.notes,
                    'evaluated_at': eval.evaluated_at.isoformat()
                }
                for eval in self.evaluations
            ])
        }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Company':
        """Create Company instance from dictionary"""
        # Deep copy to avoid modifying input
        data = data.copy()
        
        # Parse evaluations if they exist
        if 'evaluations' in data and data['evaluations']:
            evaluations = json.loads(data['evaluations'])
            for eval_data in evaluations:
                if 'skills_match' in eval_data and isinstance(eval_data['skills_match'], list):
                    eval_data['skills_match'] = eval_data['skills_match']
                if 'evaluated_at' in eval_data:
                    eval_data['evaluated_at'] = datetime.fromisoformat(eval_data['evaluated_at'])
            data['evaluations'] = [CompanyEvaluation(**eval_data) for eval_data in evaluations]
        else:
            data['evaluations'] = []
        
        # Parse dates
        if 'added_at' in data:
            data['added_at'] = datetime.fromisoformat(data['added_at'])
        
        # Convert string back to enum
        data['industry'] = CompanyIndustry(data['industry'])
        data['stage'] = CompanyStage(data['stage'])
        
        return cls(**data)
    
    def add_evaluation(self, evaluation: CompanyEvaluation) -> None:
        """Add a new evaluation to the company"""
        self.evaluations.append(evaluation)
