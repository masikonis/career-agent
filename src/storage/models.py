from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CompanyStage(str, Enum):
    """Company stages focused on early-stage opportunities"""

    IDEA = "idea"
    PRE_SEED = "pre_seed"
    MVP = "mvp"
    SEED = "seed"
    EARLY = "early"
    SERIES_A = "series_a"
    LATER = "later"


class CompanyIndustry(str, Enum):
    """Digital-first industries where marketing drives growth"""

    EDTECH = "education"
    AGENCY = "agency"
    SAAS = "saas"
    MARKETPLACE = "marketplace"
    CONTENT = "content"
    D2C = "d2c"
    NON_DIGITAL = "non_digital"


class Company(BaseModel):
    """Represents a company entity"""

    id: Optional[str] = Field(None, alias="_id")
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    industry: CompanyIndustry
    stage: CompanyStage
    website: Optional[str] = None
    company_fit_score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @field_validator("website")
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("Website URL must start with http:// or https://")
        return v

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={"json_encoders": {datetime: lambda v: v.isoformat()}},
    )


class CompanyFilters(BaseModel):
    """Filters for company search"""

    industries: Optional[List[CompanyIndustry]] = None
    stages: Optional[List[CompanyStage]] = None
    min_match_score: Optional[float] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class JobAd(BaseModel):
    """Represents a job advertisement"""

    id: Optional[str] = Field(None, alias="_id")
    company_id: str
    title: str
    description: str
    requirements: List[str]
    salary_range: Optional[tuple[int, int]] = None

    # Job status
    posted_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    active: bool = True
    archived_at: Optional[datetime] = None

    # Evaluation fields
    match_score: Optional[float] = None
    skills_match: List[str] = Field(default_factory=list)
    evaluation_notes: Optional[str] = None
    evaluated_at: Optional[datetime] = None

    model_config = ConfigDict(populate_by_name=True)
