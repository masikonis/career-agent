from typing import List, Optional
from datetime import datetime

from ..base.interfaces import BaseStorage, SearchIndex
from ..base.types import EntityID
from .types import Company, CompanyFilters

class CompanyStorage(BaseStorage[Company]):
    """Extended storage interface for company-specific operations"""

    async def find_by_industry(self, industry: str) -> List[Company]:
        """Find companies by industry"""
        pass

    async def find_by_stage(self, stage: str) -> List[Company]:
        """Find companies by stage"""
        pass

    async def add_evaluation(self, company_id: EntityID, evaluation: dict) -> bool:
        """Add an evaluation to a company"""
        pass

    async def get_evaluations(self, company_id: EntityID) -> List[dict]:
        """Get all evaluations for a company"""
        pass

class CompanySearchIndex(SearchIndex[Company]):
    """Extended search interface for company-specific search operations"""

    async def search_similar(self, company_id: EntityID, limit: int = 10) -> List[Company]:
        """Find companies similar to the given company"""
        pass

    async def search_with_filters(
        self, 
        query: str, 
        filters: CompanyFilters,
        limit: int = 10
    ) -> List[EntityID]:
        """Search companies with specific filters"""
        pass
