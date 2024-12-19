from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional

from ..base.types import EntityID


class CompanyStage(Enum):
    """Company stages focused on early-stage opportunities"""

    IDEA = "idea"
    PRE_SEED = "pre_seed"
    MVP = "mvp"
    SEED = "seed"
    EARLY = "early"
    SERIES_A = "series_a"
    LATER = "later"


class CompanyIndustry(Enum):
    """Digital-first industries where marketing drives growth"""

    EDTECH = "education"
    AGENCY = "agency"
    SAAS = "saas"
    MARKETPLACE = "marketplace"
    CONTENT = "content"
    D2C = "d2c"
    NON_DIGITAL = "non_digital"


@dataclass
class CompanyEvaluation:
    """Evaluation results for a company"""

    match_score: float
    skills_match: List[str]
    notes: Optional[str] = None
    evaluated_at: datetime = datetime.now()


@dataclass
class Company:
    """Core company entity"""

    id: Optional[EntityID]
    name: str
    description: str
    industry: CompanyIndustry
    stage: CompanyStage
    website: Optional[str] = None
    evaluations: List[CompanyEvaluation] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


@dataclass
class CompanyFilters:
    """Filters for company search"""

    industries: Optional[List[CompanyIndustry]] = None
    stages: Optional[List[CompanyStage]] = None
    min_match_score: Optional[float] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
